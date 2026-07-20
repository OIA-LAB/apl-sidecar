# SPDX-License-Identifier: FSL-1.1-ALv2
"""run-live pipeline tests — fully offline via injected fake transport.

The gate ordering is the contract under test: a leaking plan or a missing
consent must mean ZERO transport calls, and every completed (even partial)
run must leave a signed, verifiable live receipt with no key material in it.
"""
import json
import shutil
from pathlib import Path

from cli.commands import run_live
from cli.commands._verifier_boot import verify_receipt

REPO = Path(__file__).resolve().parents[1]
EXAMPLE = REPO / "examples" / "00_private_matter"
KEY = "test-key-not-real-1234567890abcdef"  # deliberately NOT sk- prefixed: repo secret-hygiene gate


class FakeTransport:
    """Answers anthropic- or openai-shaped depending on the URL. Counts calls."""

    def __init__(self, fail_hosts=(), truncate=False):
        self.calls = []
        self.fail_hosts = tuple(fail_hosts)
        self.truncate = truncate

    def __call__(self, url, headers, body, timeout=None, secrets=(), **_):
        self.calls.append(url)
        from adapters.byok._http import TransportError
        if any(host in url for host in self.fail_hosts):
            raise TransportError("provider returned HTTP 500: synthetic failure")
        if "/v1/messages" in url:
            return {"content": [{"type": "text", "text": f"live answer ({body['model']})"}],
                    "stop_reason": "max_tokens" if self.truncate else "end_turn",
                    "usage": {"input_tokens": 11, "output_tokens": 7}}
        return {"choices": [{"message": {"content": f"live answer ({body['model']})"},
                             "finish_reason": "length" if self.truncate else "stop"}],
                "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18}}


def _env(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", KEY)
    monkeypatch.setenv("OPENAI_API_KEY", KEY)
    monkeypatch.setenv("APL_OPENAI_MODEL", "test-model-b")


def test_run_live_full_flow(monkeypatch, tmp_path):
    _env(monkeypatch)
    transport = FakeTransport()
    out = tmp_path / "live-out"
    code = run_live.run(str(EXAMPLE), seat_specs=["mock_provider_a=anthropic", "mock_provider_b=openai"],
                        output=str(out), yes=True, transport=transport)
    assert code == 0
    assert len(transport.calls) == 2
    receipt = json.loads((out / "receipt.live.json").read_text(encoding="utf-8"))
    verify_receipt(receipt)  # signed with the local demo key; must verify
    events = {e["provider_id"]: e for e in receipt["provider_events"]}
    assert events["byok_anthropic_mock_provider_a"]["event_type"] == "live_response"
    assert events["byok_openai_mock_provider_b"]["event_type"] == "live_response"
    assert events["byok_anthropic_mock_provider_a"]["endpoint_host"] == "api.anthropic.com"
    assert receipt["no_single_provider_saw_full"] is True
    assert events["byok_anthropic_mock_provider_a"]["usage"]["output_tokens"] == 7
    assert events["byok_anthropic_mock_provider_a"]["response_truncated"] is False
    assert events["byok_openai_mock_provider_b"]["response_chars"] == len("live answer (test-model-b)")
    # the live receipt with its optional event fields is schema-valid
    from tests._schema_check import check
    schema = json.loads((REPO / "spec" / "receipt.schema.json").read_text(encoding="utf-8"))
    assert check(receipt, schema) == []
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
    code = run_live.run(str(leaky), seat_specs=["mock_provider_a=anthropic", "mock_provider_b=openai"],
                        output=str(tmp_path / "out"), yes=True, transport=transport)
    assert code == 1
    assert transport.calls == []  # fail-close: nothing left the machine


def test_no_consent_means_no_calls(monkeypatch, tmp_path):
    _env(monkeypatch)
    transport = FakeTransport()
    # yes=False in a non-interactive test session must refuse and make no calls
    code = run_live.run(str(EXAMPLE), seat_specs=["mock_provider_a=anthropic", "mock_provider_b=openai"],
                        output=str(tmp_path / "out"), yes=False, transport=transport)
    assert code == 1
    assert transport.calls == []


def test_partial_failure_still_leaves_signed_evidence(monkeypatch, tmp_path):
    _env(monkeypatch)
    transport = FakeTransport(fail_hosts=("api.openai.com",))
    out = tmp_path / "out"
    code = run_live.run(str(EXAMPLE), seat_specs=["mock_provider_a=anthropic", "mock_provider_b=openai"],
                        output=str(out), yes=True, transport=transport)
    assert code == 1  # partial run is an error...
    receipt = json.loads((out / "receipt.live.json").read_text(encoding="utf-8"))
    verify_receipt(receipt)  # ...but the disclosure evidence is signed and valid
    events = {e["provider_id"]: e for e in receipt["provider_events"]}
    assert events["byok_anthropic_mock_provider_a"]["event_type"] == "live_response"
    assert events["byok_openai_mock_provider_b"]["event_type"] == "no_response"
    assert events["byok_openai_mock_provider_b"]["response_sha256"] is None


def test_misconfiguration_is_exit_2(monkeypatch, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", KEY)
    monkeypatch.setenv("APL_OPENAI_MODEL", "m")
    code = run_live.run(str(EXAMPLE), seat_specs=["mock_provider_a=anthropic", "mock_provider_b=openai"],
                        output=str(tmp_path / "out"), yes=True,
                        transport=FakeTransport())
    assert code == 2


def test_chain_links_runs_into_verifiable_trail(monkeypatch, tmp_path):
    _env(monkeypatch)
    out1, out2 = tmp_path / "run1", tmp_path / "run2"
    assert run_live.run(str(EXAMPLE), seat_specs=["mock_provider_a=anthropic", "mock_provider_b=openai"],
                        output=str(out1), yes=True, transport=FakeTransport()) == 0
    assert run_live.run(str(REPO / "examples" / "01_private_code_context"),
                        seat_specs=["mock_provider_a=anthropic", "mock_provider_b=openai"], output=str(out2), yes=True,
                        transport=FakeTransport(),
                        chain=str(out1 / "receipt.live.json")) == 0
    r1 = json.loads((out1 / "receipt.live.json").read_text(encoding="utf-8"))
    r2 = json.loads((out2 / "receipt.live.json").read_text(encoding="utf-8"))
    assert r2["prev_receipt_hash"] == r1["receipt_hash"]
    from cli.commands._verifier_boot import verify_chain
    verify_chain([r1, r2])


def test_chain_refuses_invalid_previous_receipt(monkeypatch, tmp_path):
    _env(monkeypatch)
    out1 = tmp_path / "run1"
    assert run_live.run(str(EXAMPLE), seat_specs=["mock_provider_a=anthropic", "mock_provider_b=openai"],
                        output=str(out1), yes=True, transport=FakeTransport()) == 0
    tampered = json.loads((out1 / "receipt.live.json").read_text(encoding="utf-8"))
    tampered["max_single_provider_exposure"] = 0.0
    bad = tmp_path / "tampered.json"
    bad.write_text(json.dumps(tampered), encoding="utf-8")
    transport = FakeTransport()
    code = run_live.run(str(EXAMPLE), seat_specs=["mock_provider_a=anthropic", "mock_provider_b=openai"],
                        output=str(tmp_path / "run2"), yes=True,
                        transport=transport, chain=str(bad))
    assert code == 1
    assert transport.calls == []  # fail-close: chain gate fires before any socket


def test_receipt_hashes_loaded_bytes_not_a_re_read(monkeypatch, tmp_path):
    """Single-read guarantee: the receipt must hash the bytes loaded at run
    start, even if the payload file is overwritten mid-run before transmission.
    The transport's first call overwrites both payload files on disk; the
    signed receipt must still reflect the ORIGINAL content and verify."""
    _env(monkeypatch)
    ex = tmp_path / "ex"
    shutil.copytree(EXAMPLE, ex)
    payload_a = ex / "provider_a_payload.txt"
    payload_b = ex / "provider_b_payload.txt"
    original_a = payload_a.read_text(encoding="utf-8")
    original_b = payload_b.read_text(encoding="utf-8")
    from cli.commands import _common as c
    loaded_sha_a = c.text_sha256(original_a)
    loaded_sha_b = c.text_sha256(original_b)

    class OverwritingTransport(FakeTransport):
        def __call__(self, url, headers, body, timeout=None, secrets=(), **_):
            # corrupt the source files AFTER load, BEFORE this send returns
            payload_a.write_text("TAMPERED AFTER LOAD A", encoding="utf-8")
            payload_b.write_text("TAMPERED AFTER LOAD B", encoding="utf-8")
            return super().__call__(url, headers, body, timeout=timeout,
                                    secrets=secrets, **_)

    out = tmp_path / "out"
    transport = OverwritingTransport()
    code = run_live.run(str(ex), seat_specs=["mock_provider_a=anthropic",
                                             "mock_provider_b=openai"],
                        output=str(out), yes=True, transport=transport)
    assert code == 0
    # the files on disk are now the tampered content...
    assert payload_a.read_text(encoding="utf-8") == "TAMPERED AFTER LOAD A"
    receipt = json.loads((out / "receipt.live.json").read_text(encoding="utf-8"))
    verify_receipt(receipt)  # ...but the receipt is self-consistent and verifies
    events = {e["provider_id"]: e for e in receipt["provider_events"]}
    # ...and every payload hash is the ORIGINAL loaded content, never the re-read
    assert events["byok_anthropic_mock_provider_a"]["payload_sha256"] == loaded_sha_a
    assert events["byok_openai_mock_provider_b"]["payload_sha256"] == loaded_sha_b
    assert loaded_sha_a != c.text_sha256("TAMPERED AFTER LOAD A")


def test_unknown_completion_is_warned_and_signed(monkeypatch, tmp_path, capsys):
    """A provider that reports no known-complete finish signal (None,
    vendor-specific, content_filter) must yield completion="unknown" in the
    signed receipt plus a stderr warning — absence of "length" is not proof
    of completeness (vLLM/Ollama silently cap output)."""
    _env(monkeypatch)

    class NoFinishTransport(FakeTransport):
        def __call__(self, url, headers, body, timeout=None, secrets=(), **_):
            data = super().__call__(url, headers, body, timeout=timeout,
                                    secrets=secrets, **_)
            if "/v1/messages" in url:
                data["stop_reason"] = None
            else:
                data["choices"][0]["finish_reason"] = "content_filter"
            return data

    out = tmp_path / "out"
    code = run_live.run(str(EXAMPLE),
                        seat_specs=["mock_provider_a=anthropic",
                                    "mock_provider_b=openai"],
                        output=str(out), yes=True, transport=NoFinishTransport())
    assert code == 0
    receipt = json.loads((out / "receipt.live.json").read_text(encoding="utf-8"))
    verify_receipt(receipt)
    for event in receipt["provider_events"]:
        assert event["completion"] == "unknown"
        assert event["response_truncated"] is False
    err = capsys.readouterr().err
    assert 'completion="unknown"' in err
    from tests._schema_check import check
    schema = json.loads((REPO / "spec" / "receipt.schema.json").read_text(encoding="utf-8"))
    assert check(receipt, schema) == []


def test_hostile_usage_never_enters_signed_receipt(monkeypatch, tmp_path):
    """Provider-controlled usage is whitelisted and int-coerced before it can
    reach a signed artifact; junk shapes are dropped entirely."""
    _env(monkeypatch)

    class HostileUsageTransport(FakeTransport):
        def __call__(self, url, headers, body, timeout=None, secrets=(), **_):
            data = super().__call__(url, headers, body, timeout=timeout,
                                    secrets=secrets, **_)
            if "/v1/messages" in url:
                data["usage"] = "lots"  # non-dict: dropped wholesale
            else:
                data["usage"] = {"prompt_tokens": 11, "evil": {"nested": "x" * 999},
                                 "completion_tokens": "7", "total_tokens": True}
            return data

    out = tmp_path / "out"
    code = run_live.run(str(EXAMPLE),
                        seat_specs=["mock_provider_a=anthropic",
                                    "mock_provider_b=openai"],
                        output=str(out), yes=True,
                        transport=HostileUsageTransport())
    assert code == 0
    receipt = json.loads((out / "receipt.live.json").read_text(encoding="utf-8"))
    verify_receipt(receipt)
    events = {e["provider_id"]: e for e in receipt["provider_events"]}
    assert "usage" not in events["byok_anthropic_mock_provider_a"]  # non-dict
    survived = events["byok_openai_mock_provider_b"]["usage"]
    assert survived == {"prompt_tokens": 11}  # str/bool/junk keys all dropped


def test_empty_original_fails_closed(monkeypatch, tmp_path):
    """A zero-length original would make every ratio 0.0 — the run must abort
    before any accounting (and before any transport) rather than under-report."""
    import pytest
    _env(monkeypatch)
    ex = tmp_path / "ex"
    shutil.copytree(EXAMPLE, ex)
    (ex / "input.original.example.txt").write_text("", encoding="utf-8")
    transport = FakeTransport()
    with pytest.raises(SystemExit, match="under-report"):
        run_live.run(str(ex), seat_specs=["mock_provider_a=anthropic",
                                          "mock_provider_b=openai"],
                     output=str(tmp_path / "out"), yes=True, transport=transport)
    assert transport.calls == []


def test_truncated_response_is_marked_and_warned(monkeypatch, tmp_path, capsys):
    _env(monkeypatch)
    out = tmp_path / "out"
    code = run_live.run(str(EXAMPLE), seat_specs=["mock_provider_a=anthropic", "mock_provider_b=openai"],
                        output=str(out), yes=True,
                        transport=FakeTransport(truncate=True))
    assert code == 0  # truncation is honesty-marked, not a run failure
    receipt = json.loads((out / "receipt.live.json").read_text(encoding="utf-8"))
    events = {e["provider_id"]: e for e in receipt["provider_events"]}
    assert events["byok_anthropic_mock_provider_a"]["response_truncated"] is True
    assert events["byok_openai_mock_provider_b"]["response_truncated"] is True
    assert "response_truncated=true" in capsys.readouterr().err
