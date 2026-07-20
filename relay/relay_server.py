# SPDX-License-Identifier: FSL-1.1-ALv2
"""APL Demo Relay — reference prototype (P1, NOT part of the P0 offline demo).

Implements the control plane of docs/hosted_live_demo.md so the hosted demo
can be stood up without redesign: provider pool config, per-IP and
per-session rate limits, input length limits, scenario allowlist, daily cost
cap, and mock fallback. Runs locally (loopback) for development; production
deployment adds TLS, real IP extraction, persistent counters, and CAPTCHA.

Hard rules honored here:
- provider credentials only via server-side env vars named in the config;
  keys never appear in responses, logs, or errors;
- fixed workflows only; arbitrary chat is impossible by construction;
- when limits/quota are hit -> hosted-fallback (mock), never an error wall;
- operational metadata only: no raw input storage.
"""
from __future__ import annotations

import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]

DEFAULT_CONFIG = {
    "allowed_scenarios": ["private_matter", "private_code_context"],
    "per_ip_daily_limit": 5,
    "per_session_limit": 3,
    "max_input_chars": 4000,
    "daily_cost_cap_usd": 5.0,
    "est_cost_per_live_run_usd": 0.01,
    "provider_pool": [
        {"id": "pool_mock_a", "kind": "mock", "enabled": True},
        {"id": "pool_mock_b", "kind": "mock", "enabled": True},
        # live pool entries are DISABLED by default and hold no secrets:
        # {"id": "pool_openrouter", "kind": "openai_compatible", "enabled": false,
        #  "endpoint": "https://openrouter.ai/api/v1/chat/completions",
        #  "model": "<choose>", "key_env": "OPENROUTER_API_KEY"}
    ],
}

WARNING = ("Hosted demo is for testing the APL experience. Do not paste real "
           "secrets. For real sensitive content, run APL Sidecar locally or "
           "use APL Enterprise Gateway.")


class RelayState:
    """In-memory counters (production: durable store)."""

    def __init__(self, config: dict, now=time.time):
        self.config = dict(DEFAULT_CONFIG, **config)
        self.now = now
        self.ip_counts: dict[tuple[str, str], int] = {}
        self.session_counts: dict[str, int] = {}
        self.cost_by_day: dict[str, float] = {}

    def _day(self) -> str:
        return time.strftime("%Y-%m-%d", time.gmtime(self.now()))

    def check(self, ip: str, session: str, scenario: str, text: str) -> dict:
        """Returns {mode: 'live'|'fallback', 'reason': str|None} or raises ValueError."""
        cfg = self.config
        if scenario not in cfg["allowed_scenarios"]:
            raise ValueError("scenario not allowed (fixed workflows only)")
        if not text or len(text) > cfg["max_input_chars"]:
            raise ValueError(f"input length must be 1..{cfg['max_input_chars']} chars")
        day = self._day()
        if self.ip_counts.get((ip, day), 0) >= cfg["per_ip_daily_limit"]:
            return {"mode": "fallback", "reason": "per-ip daily limit reached"}
        if self.session_counts.get(session, 0) >= cfg["per_session_limit"]:
            return {"mode": "fallback", "reason": "per-session limit reached"}
        if (self.cost_by_day.get(day, 0.0) + cfg["est_cost_per_live_run_usd"]
                > cfg["daily_cost_cap_usd"]):
            return {"mode": "fallback", "reason": "daily cost cap reached"}
        return {"mode": "live", "reason": None}

    def book(self, ip: str, session: str, mode: str) -> None:
        day = self._day()
        self.ip_counts[(ip, day)] = self.ip_counts.get((ip, day), 0) + 1
        self.session_counts[session] = self.session_counts.get(session, 0) + 1
        if mode == "live":
            self.cost_by_day[day] = (self.cost_by_day.get(day, 0.0)
                                     + self.config["est_cost_per_live_run_usd"])

    def enabled_live_providers(self) -> list[dict]:
        return [p for p in self.config["provider_pool"]
                if p.get("enabled") and p.get("kind") != "mock"]


def _mock_answer(scenario: str, provider_slot: str) -> str:
    ex = {"private_matter": "00_private_matter",
          "private_code_context": "01_private_code_context"}[scenario]
    fname = "mock_answer_a.txt" if provider_slot == "a" else "mock_answer_b.txt"
    return (_REPO / "examples" / ex / fname).read_text(encoding="utf-8")


def handle_demo_run(state: RelayState, ip: str, body: dict) -> tuple[int, dict]:
    """Pure request handler (unit-testable without sockets)."""
    scenario = body.get("scenario", "")
    session = str(body.get("session_id", "anon"))[:64]
    text = body.get("payload_text", "")
    try:
        gate = state.check(ip, session, scenario, text)
    except ValueError as exc:
        return 400, {"error": "invalid_request", "detail": str(exc),
                     "warning": WARNING}
    mode = gate["mode"]
    live_pool = state.enabled_live_providers()
    if mode == "live" and not live_pool:
        mode, gate["reason"] = "fallback", "no live provider enabled"
    state.book(ip, session, mode)
    # prototype serves curated mock answers in both modes; a production
    # deployment calls the pool here for mode == "live".
    return 200, {
        "mode": "hosted-live" if mode == "live" else "hosted-fallback",
        "fallback_reason": gate["reason"],
        "warning": WARNING,
        "answers": {"provider_a": _mock_answer(scenario, "a"),
                    "provider_b": _mock_answer(scenario, "b")},
        # operational metadata only — raw input is NOT stored or echoed
        "meta": {"scenario": scenario, "input_chars": len(text)},
    }


class _Handler(BaseHTTPRequestHandler):
    state: RelayState

    def log_message(self, *a):
        pass

    def do_POST(self):  # noqa: N802
        if self.path.rstrip("/") != "/demo-run":
            return self._send(404, {"error": "not_found"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, OSError):
            return self._send(400, {"error": "invalid_json"})
        code, payload = handle_demo_run(self.state,
                                        self.client_address[0], body)
        self._send(code, payload)

    def _send(self, code: int, payload: dict) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def create_server(config: dict | None = None, port: int = 0) -> ThreadingHTTPServer:
    state = RelayState(config or {})
    handler = type("Bound", (_Handler,), {"state": state})
    return ThreadingHTTPServer(("127.0.0.1", port), handler)


if __name__ == "__main__":
    server = create_server(port=8792)
    print("APL demo relay prototype on http://127.0.0.1:8792/demo-run")
    server.serve_forever()
