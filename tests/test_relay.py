# SPDX-License-Identifier: FSL-1.1-ALv2
"""P1 relay prototype — limits, allowlist, fallback, no-key-exposure."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "relay"))

from relay_server import RelayState, handle_demo_run  # noqa: E402


def _state(**over):
    return RelayState(dict({"per_ip_daily_limit": 2, "per_session_limit": 2,
                            "daily_cost_cap_usd": 0.05,
                            "est_cost_per_live_run_usd": 0.01}, **over))


def _body(scenario="private_matter", text="fictional demo input", session="s1"):
    return {"scenario": scenario, "payload_text": text, "session_id": session}


def test_normal_run_returns_answers_and_warning():
    code, r = handle_demo_run(_state(), "1.1.1.1", _body())
    assert code == 200
    assert r["mode"] == "hosted-fallback"  # no live provider enabled by default
    assert "Do not paste real secrets" in r["warning"]
    assert r["answers"]["provider_a"] and r["answers"]["provider_b"]
    # no raw input echo — operational metadata only
    assert "payload_text" not in json.dumps(r["meta"])


def test_scenario_allowlist_fixed_workflows_only():
    code, r = handle_demo_run(_state(), "1.1.1.1", _body(scenario="free_chat"))
    assert code == 400 and "not allowed" in r["detail"]


def test_input_length_limit():
    code, r = handle_demo_run(_state(), "1.1.1.1", _body(text="x" * 5000))
    assert code == 400 and "length" in r["detail"]
    code, r = handle_demo_run(_state(), "1.1.1.1", _body(text=""))
    assert code == 400


def test_per_ip_daily_limit_falls_back():
    st = _state(provider_pool=[{"id": "live_x", "kind": "openai_compatible",
                                "enabled": True, "key_env": "NOPE"}])
    for i in range(2):
        code, r = handle_demo_run(st, "9.9.9.9", _body(session=f"s{i}"))
        assert code == 200 and r["mode"] == "hosted-live"
    code, r = handle_demo_run(st, "9.9.9.9", _body(session="s9"))
    assert r["mode"] == "hosted-fallback" and "per-ip" in r["fallback_reason"]


def test_per_session_limit_falls_back():
    st = _state(per_ip_daily_limit=99,
                provider_pool=[{"id": "live_x", "kind": "openai_compatible",
                                "enabled": True, "key_env": "NOPE"}])
    for i in range(2):
        code, r = handle_demo_run(st, f"1.2.3.{i}", _body(session="same"))
        assert r["mode"] == "hosted-live"
    code, r = handle_demo_run(st, "1.2.3.9", _body(session="same"))
    assert r["mode"] == "hosted-fallback" and "session" in r["fallback_reason"]


def test_daily_cost_cap_falls_back():
    st = _state(per_ip_daily_limit=99, per_session_limit=99,
                daily_cost_cap_usd=0.02,
                provider_pool=[{"id": "live_x", "kind": "openai_compatible",
                                "enabled": True, "key_env": "NOPE"}])
    modes = []
    for i in range(4):
        code, r = handle_demo_run(st, "8.8.8.8", _body(session=f"s{i}"))
        modes.append(r["mode"])
    assert modes[:2] == ["hosted-live", "hosted-live"]
    assert modes[2] == "hosted-fallback"


def test_no_key_material_in_any_response():
    st = _state(provider_pool=[{"id": "live_x", "kind": "openai_compatible",
                                "enabled": True,
                                "key_env": "OPENROUTER_API_KEY"}])
    code, r = handle_demo_run(st, "1.1.1.1", _body())
    dump = json.dumps(r)
    assert "key" not in dump.lower() or "key_env" not in dump
    assert "OPENROUTER_API_KEY" not in dump
