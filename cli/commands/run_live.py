"""apl run-live -- BYOK reference: send approved payloads to real providers.

The first command in this repo that touches the network, so it earns that
right in order:

1. LEAK GATE   — the exact rule `apl mask` enforces; a failing plan is never
                 transmitted (fail-close, exit 1, zero network calls made).
2. PRE-FLIGHT  — show exactly what will leave the machine, to whom, and how
                 much, then require explicit consent (or --yes).
3. TRANSMIT    — one user message per provider, containing only the approved
                 payload. Keys come from the environment and are scrubbed
                 from every error path; they never appear in receipts.
4. RECEIPT     — Ed25519-signed, event_type "live_response", verified before
                 the command reports success. A partial run (one provider
                 failed) still produces a signed receipt recording exactly
                 which payload was disclosed — failures leave evidence too.

Rehydration stays local: provider answers plus local-only context are
combined on this machine only (combined_answer.local.md).
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any, Callable

from adapters.base import ProviderRequest
from adapters.byok._http import ByokConfigError, TransportError
from adapters.byok.anthropic_provider import AnthropicAdapter
from adapters.byok.openai_provider import OpenAICompatAdapter

from . import _common as c
from . import _signing

SEAT_PAYLOAD = {"a": "mock_provider_a", "b": "mock_provider_b"}
KINDS = ("anthropic", "openai")

Transport = Callable[..., dict[str, Any]]


def build_seat(kind: str, seat: str, transport: Transport | None = None):
    if kind == "anthropic":
        return AnthropicAdapter.from_env(
            seat=seat, provider_id=f"byok_anthropic_{seat}", transport=transport)
    if kind == "openai":
        return OpenAICompatAdapter.from_env(
            seat=seat, provider_id=f"byok_openai_{seat}", transport=transport)
    raise ByokConfigError(f"unknown provider kind: {kind!r} (expected one of {KINDS})")


def build_receipt_body(paths: dict, seats: dict, responses: dict,
                       prev_hash: str | None = None) -> dict:
    """Live variant of the RECEIPT_STANDARD body: same exposure accounting,
    event_type live_response/no_response, plus signature-covered optional
    fields per event: endpoint_host, model, response_chars,
    response_truncated, and provider-reported usage."""
    view = c.exposure_view(paths)
    local_only = c.load_local_only(paths)
    plan = c.load_masking_plan(paths)
    policy = c.load_policy_manifest()
    events, exposures = [], []
    for seat, adapter in seats.items():
        info = view["providers"][SEAT_PAYLOAD[seat]]
        resp = responses.get(seat)
        text = resp.text if resp else None
        event = {"provider_id": adapter.provider_id,
                 "payload_sha256": info["payload_sha256"],
                 "payload_chars": info["chars"],
                 "response_sha256": c.text_sha256(text) if text else None,
                 "response_chars": len(text) if text else None,
                 "event_type": "live_response" if text else "no_response",
                 "endpoint_host": adapter.endpoint_host,
                 "model": adapter.model}
        if resp is not None:
            event["response_truncated"] = bool(resp.metadata.get("truncated"))
            usage = resp.metadata.get("usage")
            if usage is not None:
                event["usage"] = usage
        events.append(event)
        exposures.append({"provider_id": adapter.provider_id,
                          "exposure_ratio": info["exposure_ratio"]})
    return {
        "run_id": c.new_ulid(),
        "task_type": plan["task_type"],
        "policy_id": policy["policy_id"],
        "provider_events": events,
        "local_only_hashes": [
            {"field": k, "sha256": c.text_sha256(json.dumps(v) if not isinstance(v, str) else v)}
            for k, v in sorted(local_only.items())],
        "single_provider_exposure": exposures,
        "max_single_provider_exposure": view["max_single_provider_exposure"],
        "no_single_provider_saw_full": view["no_single_provider_saw_full"],
        "prev_receipt_hash": prev_hash,
        "masking_level": "guided_curated_p0",
        "provenance": {
            "apl_sidecar_version": "0.1.0-draft",
            "receipt_schema_version": "0.1.0-draft",
            "policy_version": policy["policy_version"],
            "example_id": paths["dir"].name,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    }


def _preflight(paths: dict, seats: dict) -> None:
    view = c.exposure_view(paths)
    print("=" * 64)
    print(f"APL RUN-LIVE -- {paths['dir'].name} (NETWORK, bring-your-own-key)")
    print("=" * 64)
    for seat, adapter in seats.items():
        info = view["providers"][SEAT_PAYLOAD[seat]]
        print(f"seat {seat.upper()}: {adapter.provider_id}"
              f" -> host {adapter.endpoint_host}, model {adapter.model}")
        print(f"        payload {info['chars']} chars"
              f" (exposure ratio {info['exposure_ratio']})")
    print(f"no_single_provider_saw_full: {view['no_single_provider_saw_full']}")
    print("local-only fields never transmitted:",
          ", ".join(sorted(c.load_local_only(paths))) or "(none)")


def _confirm(yes: bool) -> bool:
    if yes:
        return True
    if not sys.stdin.isatty():
        print("\nRefusing to transmit: non-interactive session without --yes.",
              file=sys.stderr)
        return False
    return input("\nType 'send' to transmit these payloads, anything else aborts: ") == "send"


def _write_combined(out_dir: Path, paths: dict, seats: dict,
                    responses: dict) -> Path:
    local_only = c.load_local_only(paths)
    parts = ["# Combined answer (assembled locally)\n"]
    for seat, adapter in seats.items():
        parts.append(f"\n## Seat {seat.upper()} — {adapter.provider_id} "
                     f"(saw only its payload)\n")
        resp = responses.get(seat)
        parts.append((resp.text if resp else "(no response — provider call failed)") + "\n")
    parts.append("\n## Local-only context (reintroduced on this machine only)\n")
    for fld, value in sorted(local_only.items()):
        parts.append(f"- **{fld}**: {value}\n")
    combined = out_dir / "combined_answer.local.md"
    combined.write_text("".join(parts), encoding="utf-8")
    return combined


def run(example_dir: str, a_kind: str = "anthropic", b_kind: str = "openai",
        output: str = "apl-live-out", yes: bool = False,
        transport: Transport | None = None, chain: str | None = None) -> int:
    paths = c.example_paths(example_dir)

    # 1. LEAK GATE — same rule as `apl mask`, enforced before any socket opens.
    leaks = c.leak_findings(paths)
    if leaks:
        print("LEAK CHECK FAILED -- refusing to transmit:", file=sys.stderr)
        for leak in leaks:
            print(f"  ! {leak}", file=sys.stderr)
        return 1

    # 1b. CHAIN GATE — refuse to chain onto a receipt that does not verify.
    # Fail-close, still before any socket opens: a broken chain is not
    # something to discover after the disclosure already happened.
    prev_hash = None
    if chain:
        sys.path.insert(0, str(c.REPO / "verifier"))
        import apl_verify  # noqa: E402
        try:
            prev = json.loads(Path(chain).read_text(encoding="utf-8"))
            apl_verify.verify_receipt(prev)
        except Exception as exc:  # noqa: BLE001 — any failure refuses the chain
            print(f"CHAIN REFUSED -- previous receipt invalid: {exc}", file=sys.stderr)
            return 1
        prev_hash = prev["receipt_hash"]

    try:
        seats = {"a": build_seat(a_kind, "a", transport),
                 "b": build_seat(b_kind, "b", transport)}
    except ByokConfigError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2

    # 2. PRE-FLIGHT + consent.
    _preflight(paths, seats)
    if not _confirm(yes):
        print("Aborted. Nothing was transmitted.")
        return 1

    # 3. TRANSMIT.
    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)
    responses: dict[str, object | None] = {}
    failures = []
    for seat, adapter in seats.items():
        payload = c.read_text(paths["payloads"][SEAT_PAYLOAD[seat]])
        try:
            result = adapter.complete(ProviderRequest(prompt=payload, model=adapter.model))
            responses[seat] = result
            (out_dir / f"live_answer_{seat}.local.txt").write_text(
                result.text, encoding="utf-8")
            print(f"[seat {seat}] live response received ({len(result.text)} chars)"
                  f" from {adapter.endpoint_host}")
            if result.metadata.get("truncated"):
                print(f"[seat {seat}] WARNING: provider truncated this response"
                      " at its length limit; the receipt records"
                      " response_truncated=true so a partial answer can never"
                      " masquerade as complete.", file=sys.stderr)
        except TransportError as exc:
            responses[seat] = None
            failures.append(seat)
            print(f"[seat {seat}] FAILED: {exc}", file=sys.stderr)

    # 4. RECEIPT — signed and verified even for partial runs: what was
    # disclosed was disclosed, whether or not an answer came back.
    key, key_id = _signing.ensure_local_keypair()
    receipt = _signing.sign_receipt(
        build_receipt_body(paths, seats, responses, prev_hash), key, key_id)
    receipt_path = out_dir / "receipt.live.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")

    repo_root = c.REPO
    sys.path.insert(0, str(repo_root / "verifier"))
    import apl_verify  # noqa: E402
    apl_verify.verify_receipt(receipt)  # raises on any failure — fail-close

    combined = _write_combined(out_dir, paths, seats, responses)
    print(f"\nSigned receipt written and verified: {receipt_path}")
    if prev_hash:
        print(f"Chained onto verified receipt {prev_hash[:12]}…"
              f"  (verify both: apl verify {chain} {receipt_path})")
    print(f"receipt_hash: {receipt['receipt_hash']}")
    print(f"Local rehydration:  {combined}")
    print(f"Verify any time:    apl verify {receipt_path}")
    if failures:
        print(f"\nPartial run: seat(s) {', '.join(failures)} failed;"
              " the receipt records the disclosure regardless.", file=sys.stderr)
        return 1
    return 0
