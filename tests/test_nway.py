"""N-way fragmentation — the ruling's contract under test.

Seats are not providers, providers are not trust domains: the receipt must
aggregate exposure by who actually accumulates the fragments, a port must
never count as an isolation boundary, and every seat-mapping mistake must
mean exit 2 with zero transport calls.
"""
import json
import sys
from pathlib import Path

import pytest

from cli.commands import _common as c
from cli.commands import run_live, run_mock
from tests._schema_check import check as schema_check
from tests.test_run_live import KEY, FakeTransport
from verifier.apl_verify import VerifyError, verify_receipt, _check_trust_domain_consistency

REPO = Path(__file__).resolve().parents[1]
THREE_WAY = REPO / "examples" / "02_market_entry_three_way"
LEGACY = REPO / "examples" / "00_private_idea"


def _env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    monkeypatch.setenv("OPENAI_API_KEY", KEY)
    monkeypatch.setenv("APL_OPENAI_MODEL", "test-model")


# ---------------------------- declarations ----------------------------

def test_fragments_declaration_parsed():
    paths = c.example_paths(THREE_WAY)
    assert [f["id"] for f in paths["fragments"]] == ["pricing", "channel", "risk"]
    assert set(paths["payloads"]) == {"pricing", "channel", "risk"}
    for f in paths["fragments"]:
        assert f["payload"].exists() and f["mock_answer"].exists()


def test_legacy_fallback_unchanged():
    paths = c.example_paths(LEGACY)
    assert [f["id"] for f in paths["fragments"]] == ["mock_provider_a", "mock_provider_b"]
    assert set(paths["payloads"]) == {"mock_provider_a", "mock_provider_b"}


@pytest.mark.parametrize("count", [1, 6])
def test_fragment_count_bounds_hard_limit(tmp_path, count):
    d = tmp_path / "ex"
    d.mkdir()
    frags = "\n".join(
        f"  - id: f{i}\n    payload: p{i}.txt" for i in range(count))
    (d / "masking_plan.yaml").write_text(
        f"task_type: bounds_check\nfragments:\n{frags}\n", encoding="utf-8")
    for i in range(count):
        (d / f"p{i}.txt").write_text("payload", encoding="utf-8")
    (d / "local_only.json").write_text("{}", encoding="utf-8")
    (d / "input.original.example.txt").write_text("original text", encoding="utf-8")
    with pytest.raises(SystemExit):
        c.example_paths(d)


# ------------------------- trust-domain rule --------------------------

def test_trust_domain_rule_ports_and_vendors():
    assert c.trust_domain("api.openai.com") == "openai"
    assert c.trust_domain("api.anthropic.com") == "anthropic"
    # a port is not an isolation boundary
    assert c.trust_domain("127.0.0.1:9998") == c.trust_domain("127.0.0.1:9999")
    # same kind, genuinely different endpoint = different domain
    assert c.trust_domain("api.openai.com") != c.trust_domain("127.0.0.1:8793")


# ------------------------ seat mapping fail-close ---------------------

@pytest.mark.parametrize("specs", [
    ["pricing=anthropic", "channel=openai"],                        # missing seat
    ["pricing=anthropic", "channel=openai", "risk=openai",
     "pricing=openai"],                                             # duplicate
    ["pricing=anthropic", "channel=openai", "ghost=openai"],        # unknown id
    ["pricing=anthropic", "channel=openai", "risk=grok"],           # unknown kind
    ["pricing", "channel=openai", "risk=openai"],                   # malformed
    None,                                                           # 3-way needs names
])
def test_seat_spec_errors_exit2_zero_transport(monkeypatch, tmp_path, specs):
    _env(monkeypatch)
    transport = FakeTransport()
    code = run_live.run(str(THREE_WAY), seat_specs=specs,
                        output=str(tmp_path / "o"), yes=True, transport=transport)
    assert code == 2
    assert transport.calls == []  # zero transport on any mapping error


# ------------------- ruling test 1: three distinct domains ------------

def test_three_distinct_trust_domains(monkeypatch, tmp_path):
    _env(monkeypatch)
    # risk seat: same openai kind, but a loopback endpoint -> its own domain
    monkeypatch.setenv("APL_OPENAI_BASE_URL_RISK", "http://127.0.0.1:9999/v1")
    transport = FakeTransport()
    out = tmp_path / "o"
    code = run_live.run(str(THREE_WAY),
                        seat_specs=["pricing=anthropic", "channel=openai",
                                    "risk=openai"],
                        output=str(out), yes=True, transport=transport)
    assert code == 0 and len(transport.calls) == 3
    receipt = json.loads((out / "receipt.live.json").read_text(encoding="utf-8"))
    verify_receipt(receipt)
    domains = {d["trust_domain"]: d for d in receipt["trust_domain_exposure"]}
    assert set(domains) == {"anthropic", "openai", "127.0.0.1"}
    assert all(len(d["seat_ids"]) == 1 for d in domains.values())
    # with one seat per domain, the domain max equals the seat max
    assert receipt["max_single_trust_domain_exposure"] == \
        receipt["max_single_seat_exposure"]
    assert receipt["max_single_provider_exposure"] == \
        receipt["max_single_trust_domain_exposure"]
    assert receipt["no_single_trust_domain_received_all_fragments"] is True
    # schema: additive v0.2 receipt still validates
    schema = json.loads((REPO / "spec" / "receipt.schema.json").read_text(encoding="utf-8"))
    assert not schema_check(receipt, schema)


# ---------------- ruling test 2: all seats on one vendor --------------

def test_all_seats_same_domain_aggregates_and_warns(monkeypatch, tmp_path, capsys):
    _env(monkeypatch)
    transport = FakeTransport()
    out = tmp_path / "o"
    code = run_live.run(str(THREE_WAY),
                        seat_specs=["pricing=openai", "channel=openai",
                                    "risk=openai"],
                        output=str(out), yes=True, transport=transport)
    assert code == 0
    err = capsys.readouterr().err
    assert 'resolve to the same trust domain "openai"' in err
    assert "Fragment count does not reduce exposure" in err
    receipt = json.loads((out / "receipt.live.json").read_text(encoding="utf-8"))
    verify_receipt(receipt)
    domains = {d["trust_domain"]: d for d in receipt["trust_domain_exposure"]}
    assert set(domains) == {"openai"}
    assert sorted(domains["openai"]["seat_ids"]) == ["channel", "pricing", "risk"]
    per_seat = [e["exposure_ratio"] for e in receipt["single_provider_exposure"]]
    aggregated = round(sum(per_seat), 6)
    assert abs(domains["openai"]["exposure_ratio"] - aggregated) < 1e-6
    # the vendor got everything: the receipt must say so, loudly
    assert receipt["no_single_trust_domain_received_all_fragments"] is False
    # and the legacy max MUST be the aggregate, never a ~1/3 per-seat figure
    assert receipt["max_single_provider_exposure"] == aggregated
    assert receipt["max_single_provider_exposure"] > \
        receipt["max_single_seat_exposure"]


# ------------- verifier recomputes the aggregation itself -------------

def test_verifier_rejects_inconsistent_trust_domain_claims(monkeypatch, tmp_path):
    _env(monkeypatch)
    transport = FakeTransport()
    out = tmp_path / "o"
    assert run_live.run(str(THREE_WAY),
                        seat_specs=["pricing=openai", "channel=openai",
                                    "risk=openai"],
                        output=str(out), yes=True, transport=transport) == 0
    receipt = json.loads((out / "receipt.live.json").read_text(encoding="utf-8"))
    # understate the aggregate the way a misleading receipt would
    receipt["trust_domain_exposure"][0]["exposure_ratio"] = \
        receipt["max_single_seat_exposure"]
    with pytest.raises(VerifyError):
        _check_trust_domain_consistency(receipt)
    with pytest.raises(VerifyError):  # and the full verifier path fails too
        verify_receipt(receipt)


# ----------------------- offline paths for 3-way ----------------------

def test_run_mock_three_way_signs_and_verifies(tmp_path):
    assert run_mock.run(str(THREE_WAY)) == 0
    receipt = json.loads((THREE_WAY / "receipt.local.json").read_text(encoding="utf-8"))
    verify_receipt(receipt)
    ids = {e["provider_id"] for e in receipt["provider_events"]}
    assert ids == {"pricing", "channel", "risk"}
    assert receipt["no_single_provider_saw_full"] is True


def test_preview_and_mask_three_way(capsys):
    from cli.commands import mask, preview
    assert mask.run(str(THREE_WAY)) == 0
    assert preview.run(str(THREE_WAY)) == 0
    out = capsys.readouterr().out
    assert "PRICING" in out and "CHANNEL" in out and "RISK" in out


def test_run_live_help_documents_named_seats():
    apl = (REPO / "cli" / "apl.py").read_text(encoding="utf-8")
    assert "--seat FRAGMENT_ID=KIND" in apl
    assert "2-5" in apl


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
