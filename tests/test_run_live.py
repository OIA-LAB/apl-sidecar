"""run-live pipeline tests — fully offline via injected fake transport.

The gate ordering is the contract under test: a leaking plan or a missing
consent must mean ZERO transport calls, and every completed (even partial)
run must leave a signed, verifiable live receipt with no key material in it.
"""
import json
import shutil
from pathlib import Path

from cli.commands import run_live
from verifier.apl_verify import verify_receipt

REPO = Path(__file__).resolve().parents[1]
EXAMPLE = REPO / "examples" / "00_private_idea"
KEY = "test-key-not-real-1234567890abcdef"  # deliberately NOT sk- prefixed: repo secret-hygiene gate


class FakeTransport:
    """Answers anthropic- or openai-shaped depending on the URL. Counts calls."""

    def __init__(self, fail_hosts=()):
        self.calls = []
        self.fail_hosts = tuple(fail_hosts)

    def __call__(self, url, headers, body, timeout=None, secrets=(), **_):
        self.calls.append(url)
        from adapters.byok._http import TransportError
        if any(host in url for host in self.fail_hosts):
            raise TransportError("provider returned HTTP 500: synthetic failure")
        if "/v1/messages" in url:
            return {"content": [{"type": "text", "text": f"live answer ({body['model']})"}],
                    "stop_reason": "end_turn"}
        return {"choices": [{"message": {"content": f"live answer ({body['model']})"},
                             "finish_reason": "stop"}]}


def _env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    monkeypatch.setenv("OPENAI_API_KEY", KEY)
    monkeypatch.setenv("APL_OPENAI_MODEL", "test-model-b")


def test_run_live_full_flow(monkeypatch, tmp_path):
    _env(monkeypatch)
    transport = FakeTransport()
    out = tmp_path / "live-out"
    code = run_live.run(str(EXAMPLE), "anthropic", "openai",
                        output=str(out), yes=True, transport=transport)
    assert code == 0
    assert len(transport.calls) == 2
    receipt = json.loads((out / "receipt.live.json").read_text(encoding="utf-8"))
    verify_receipt(receipt)  # signed with the local demo key; must verify
    events = {e["provider_id"]: e for e in receipt["provider_events"]}
    assert events["byok_anthropic_a"]["event_type"] == "live_response"
    assert events["byok_openai_b"]["event_type"] == "live_response"
    assert events["byok_anthropic_a"]["endpoint_host"] == "api.anthropic.com"
    assert receipt["no_single_provider_saw_full"] is True
    # key hygiene: no key material in any artifact
    for artifact in out.iterdir():
        assert KEY not in artifact.read_text(encoding="utf-8")
    combined = (out / "combined_answer.local.md").read_text(encoding="utf-8")
    assert "reintroduced on this machine only" in combined


def test_leak_gate_blocks_before_any_network(monkeypatch, tmp_path):
    _env(monkeypatch)
    leaky = tmp_path / "leaky_example"
    shutil.copytree(EXAMPLE, leaky)
    local_only = json.loads((leaky / "local_only.json").read_text(encoding="utf-8"))
    secret_value = next(v for v in local_only.values() if isinstance(v, str) and len(v) >= 4)
    payload = leaky / "provider_a_payload.txt"
    payload.write_text(payload.read_text(encoding="utf-8") + "\n" + secret_value,
                       encoding="utf-8")
    transport = FakeTransport()
    code = run_live.run(str(leaky), "anthropic", "openai",
                        output=str(tmp_path / "out"), yes=True, transport=transport)
    assert code == 1
    assert transport.calls == []  # fail-close: nothing left the machine


def test_no_consent_means_no_calls(monkeypatch, tmp_path):
    _env(monkeypatch)
    transport = FakeTransport()
    # yes=False in a non-interactive test session must refuse and make no calls
    code = run_live.run(str(EXAMPLE), "anthropic", "openai",
                        output=str(tmp_path / "out"), yes=False, transport=transport)
    assert code == 1
    assert transport.calls == []


def test_partial_failure_still_leaves_signed_evidence(monkeypatch, tmp_path):
    _env(monkeypatch)
    transport = FakeTransport(fail_hosts=("api.openai.com",))
    out = tmp_path / "out"
    code = run_live.run(str(EXAMPLE), "anthropic", "openai",
                        output=str(out), yes=True, transport=transport)
    assert code == 1  # partial run is an error...
    receipt = json.loads((out / "receipt.live.json").read_text(encoding="utf-8"))
    verify_receipt(receipt)  # ...but the disclosure evidence is signed and valid
    events = {e["provider_id"]: e for e in receipt["provider_events"]}
    assert events["byok_anthropic_a"]["event_type"] == "live_response"
    assert events["byok_openai_b"]["event_type"] == "no_response"
    assert events["byok_openai_b"]["response_sha256"] is None


def test_misconfiguration_is_exit_2(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", KEY)
    monkeypatch.setenv("APL_OPENAI_MODEL", "m")
    code = run_live.run(str(EXAMPLE), "anthropic", "openai",
                        output=str(tmp_path / "out"), yes=True,
                        transport=FakeTransport())
    assert code == 2
