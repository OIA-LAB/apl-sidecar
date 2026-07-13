"""apl run-live -- BYOK reference: send approved payloads to real providers.

The first command in this repo that touches the network, so it earns that
right in order:

1. LEAK GATE   — the exact rule `apl mask` enforces; a failing plan is never
                 transmitted (fail-close, exit 1, zero network calls made).
2. PRE-FLIGHT  — show exactly what will leave the machine, to whom, and how
                 much — per seat AND per trust domain — then require explicit
                 consent (or --yes).
3. TRANSMIT    — one user message per seat, containing only the approved
                 payload. Keys come from the environment and are scrubbed
                 from every error path; they never appear in receipts.
4. RECEIPT     — Ed25519-signed, event_type "live_response", verified before
                 the command reports success. A partial run (one provider
                 failed) still produces a signed receipt recording exactly
                 which payload was disclosed — failures leave evidence too.

Seats are not providers, and providers are not trust domains. Three seats
that all resolve to the same vendor mean that vendor received ALL of those
fragments — so exposure is accounted twice and both are signed into the
receipt: per seat (max_single_seat_exposure) and aggregated per trust
domain (max_single_trust_domain_exposure, and the legacy
max_single_provider_exposure equals the trust-domain maximum). Fragment
count alone reduces nothing; docs/fragmentation.md spells out the rule.

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

KINDS = ("anthropic", "openai")
RECEIPT_SCHEMA_VERSION = "0.2.0-draft"  # additive fields only; 0.1 receipts stay valid

# Provider-reported usage is provider-asserted, unverified data. Only these
# keys, coerced to int, may enter the signed receipt — a signed artifact must
# never lend authority to arbitrary provider-controlled structure.
_USAGE_KEYS = ("input_tokens", "output_tokens", "total_tokens",
               "prompt_tokens", "completion_tokens")


def _normalize_usage(usage: Any) -> dict[str, int] | None:
    """Whitelist + int-coerce provider usage; None when nothing survives."""
    if not isinstance(usage, dict):
        return None
    clean: dict[str, int] = {}
    for key in _USAGE_KEYS:
        value = usage.get(key)
        if isinstance(value, bool):  # bool is an int subclass; reject it
            continue
        if isinstance(value, int):
            clean[key] = value
        elif isinstance(value, float) and value.is_integer():
            clean[key] = int(value)
    return clean or None

Transport = Callable[..., dict[str, Any]]


def build_seat(kind: str, seat: str, transport: Transport | None = None):
    if kind == "anthropic":
        return AnthropicAdapter.from_env(
            seat=seat, provider_id=f"byok_anthropic_{seat}", transport=transport)
    if kind == "openai":
        return OpenAICompatAdapter.from_env(
            seat=seat, provider_id=f"byok_openai_{seat}", transport=transport)
    raise ByokConfigError(f"unknown provider kind: {kind!r} (expected one of {KINDS})")


def resolve_seats(paths: dict, seat_specs: list[str] | None,
                  transport: Transport | None = None) -> dict:
    """Map fragment ids to adapters from named --seat specs (fail-close).

    Rules (documented in --help):
    - two fragments and no --seat: legacy default anthropic, openai;
    - three or more fragments: every fragment must be explicitly named;
    - unknown id, duplicate id, missing or extra seats: ByokConfigError
      (exit 2, zero transport).
    """
    fragment_ids = [f["id"] for f in paths["fragments"]]
    if not seat_specs:
        if len(fragment_ids) == 2:
            return {fragment_ids[0]: build_seat("anthropic", fragment_ids[0], transport),
                    fragment_ids[1]: build_seat("openai", fragment_ids[1], transport)}
        raise ByokConfigError(
            f"{len(fragment_ids)} fragments declared; every seat must be named "
            "explicitly: --seat <fragment_id>=<anthropic|openai>")
    mapping: dict[str, str] = {}
    for spec in seat_specs:
        fid, sep, kind = spec.partition("=")
        if not sep or not fid or not kind:
            raise ByokConfigError(f"--seat expects <fragment_id>=<kind>, got {spec!r}")
        if fid not in fragment_ids:
            raise ByokConfigError(
                f"unknown fragment id {fid!r} (declared: {', '.join(fragment_ids)})")
        if fid in mapping:
            raise ByokConfigError(f"duplicate --seat for fragment {fid!r}")
        if kind not in KINDS:
            raise ByokConfigError(f"unknown provider kind: {kind!r} (expected one of {KINDS})")
        mapping[fid] = kind
    missing = [fid for fid in fragment_ids if fid not in mapping]
    if missing:
        raise ByokConfigError("missing --seat for fragment(s): " + ", ".join(missing))
    return {fid: build_seat(mapping[fid], fid, transport) for fid in fragment_ids}


def trust_domain_view(inputs: dict, seats: dict) -> dict:
    """Per-seat and per-trust-domain exposure accounting.

    A seat is one fragment sent to one adapter. A trust domain is who
    actually accumulates the fragments (c.trust_domain rule: known vendor
    hosts collapse to the vendor; anything else aggregates by host with the
    port stripped). Ratios are summed per domain; a domain that received
    every fragment is flagged. Operates on the single-read in-memory buffers
    so the numbers can never diverge from the transmitted bytes.
    """
    view = c.exposure_view_from_texts(inputs["original"], inputs["payloads"])
    per_seat = {}
    domains: dict[str, dict] = {}
    for fid, adapter in seats.items():
        info = view["providers"][fid]
        domain = c.trust_domain(adapter.endpoint_host)
        per_seat[fid] = {"exposure_ratio": info["exposure_ratio"],
                         "chars": info["chars"],
                         "payload_sha256": info["payload_sha256"],
                         "trust_domain": domain}
        entry = domains.setdefault(domain, {"exposure_ratio": 0.0, "seat_ids": []})
        entry["exposure_ratio"] = round(entry["exposure_ratio"] + info["exposure_ratio"], 6)
        entry["seat_ids"].append(fid)
    all_seats = set(seats)
    return {
        "exposure_view": view,
        "per_seat": per_seat,
        "domains": domains,
        "max_single_seat_exposure": round(
            max((s["exposure_ratio"] for s in per_seat.values()), default=0.0), 6),
        "max_single_trust_domain_exposure": round(
            max((d["exposure_ratio"] for d in domains.values()), default=0.0), 6),
        "no_single_trust_domain_received_all_fragments": not any(
            set(d["seat_ids"]) == all_seats for d in domains.values()),
    }


def build_receipt_body(paths: dict, inputs: dict, seats: dict, responses: dict,
                       prev_hash: str | None = None) -> dict:
    """Live receipt body per RECEIPT_STANDARD v0.2 (additive fields).

    Exposure is signed twice, deliberately:
    - single_provider_exposure / max_single_seat_exposure: per seat;
    - trust_domain_exposure / max_single_trust_domain_exposure: aggregated
      by who actually receives the fragments.
    The legacy max_single_provider_exposure field carries the trust-domain
    maximum — per-seat numbers must never understate a vendor that holds
    several fragments. Every event signs seat_id, provider_kind,
    trust_domain and endpoint_host so the aggregation is recomputable from
    the receipt alone.
    """
    tview = trust_domain_view(inputs, seats)
    local_only = inputs["local_only"]
    plan = inputs["masking_plan"]
    policy = c.load_policy_manifest()
    events, exposures = [], []
    for fid, adapter in seats.items():
        info = tview["per_seat"][fid]
        resp = responses.get(fid)
        text = resp.text if resp else None
        event = {"provider_id": adapter.provider_id,
                 "seat_id": fid,
                 "provider_kind": ("anthropic" if isinstance(adapter, AnthropicAdapter)
                                   else "openai"),
                 "trust_domain": info["trust_domain"],
                 "payload_sha256": info["payload_sha256"],
                 "payload_chars": info["chars"],
                 "response_sha256": c.text_sha256(text) if text else None,
                 "response_chars": len(text) if text else None,
                 "event_type": "live_response" if text else "no_response",
                 "endpoint_host": adapter.endpoint_host,
                 "model": adapter.model}
        if resp is not None:
            completion = resp.metadata.get("completion", "unknown")
            # completion is the source of truth; response_truncated is the
            # legacy boolean projection (true only for known truncation).
            event["completion"] = completion
            event["response_truncated"] = completion == "truncated"
            usage = _normalize_usage(resp.metadata.get("usage"))
            if usage is not None:
                event["usage"] = usage
        events.append(event)
        exposures.append({"provider_id": adapter.provider_id,
                          "exposure_ratio": info["exposure_ratio"]})
    # Fail-close on duplicates before signing: a receipt whose events share a
    # seat_id/provider_id could hide one seat's exposure behind another's.
    for label, values in (("seat_id", [e["seat_id"] for e in events]),
                          ("provider_id", [e["provider_id"] for e in events])):
        if len(values) != len(set(values)):
            raise ValueError(f"duplicate {label} in provider events; refusing to sign")
    return {
        "run_id": c.new_ulid(),
        "task_type": plan["task_type"],
        "policy_id": policy["policy_id"],
        "provider_events": events,
        "local_only_hashes": [
            {"field": k, "sha256": c.text_sha256(json.dumps(v) if not isinstance(v, str) else v)}
            for k, v in sorted(local_only.items())],
        "single_provider_exposure": exposures,
        "max_single_seat_exposure": tview["max_single_seat_exposure"],
        "trust_domain_exposure": [
            {"trust_domain": dom, "exposure_ratio": d["exposure_ratio"],
             "seat_ids": d["seat_ids"]}
            for dom, d in sorted(tview["domains"].items())],
        "max_single_trust_domain_exposure": tview["max_single_trust_domain_exposure"],
        "no_single_trust_domain_received_all_fragments":
            tview["no_single_trust_domain_received_all_fragments"],
        # legacy field: MUST carry the trust-domain maximum, never the
        # per-seat maximum — a vendor holding 3 fragments is one provider.
        "max_single_provider_exposure": tview["max_single_trust_domain_exposure"],
        "no_single_provider_saw_full": tview["exposure_view"]["no_single_provider_saw_full"],
        "prev_receipt_hash": prev_hash,
        "masking_level": "guided_curated_p0",
        "provenance": {
            "apl_sidecar_version": "0.1.0-draft",
            "receipt_schema_version": RECEIPT_SCHEMA_VERSION,
            "policy_version": policy["policy_version"],
            "example_id": paths["dir"].name,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    }


def _same_domain_warnings(tview: dict) -> list[str]:
    warnings = []
    for dom, d in sorted(tview["domains"].items()):
        if len(d["seat_ids"]) > 1:
            warnings.append(
                f"WARNING: {len(d['seat_ids'])} seats resolve to the same trust "
                f"domain \"{dom}\". Fragment count does not reduce exposure to "
                f"that provider: it receives {d['exposure_ratio']:.1%} combined "
                f"({', '.join(d['seat_ids'])}).")
    return warnings


def _preflight(paths: dict, inputs: dict, seats: dict) -> None:
    tview = trust_domain_view(inputs, seats)
    print("=" * 64)
    print(f"APL RUN-LIVE -- {paths['dir'].name} (NETWORK, bring-your-own-key)")
    print("=" * 64)
    for fid, adapter in seats.items():
        info = tview["per_seat"][fid]
        print(f"seat {fid}: {adapter.provider_id}"
              f" -> host {adapter.endpoint_host}, model {adapter.model},"
              f" trust domain {info['trust_domain']}")
        print(f"        payload {info['chars']} chars"
              f" (seat exposure ratio {info['exposure_ratio']})")
    print("-" * 64)
    for dom, d in sorted(tview["domains"].items()):
        print(f"trust domain {dom}: {d['exposure_ratio']:.1%} combined"
              f" ({len(d['seat_ids'])} seat(s): {', '.join(d['seat_ids'])})")
    print(f"max_single_seat_exposure:         {tview['max_single_seat_exposure']}")
    print(f"max_single_trust_domain_exposure: {tview['max_single_trust_domain_exposure']}")
    print("no_single_trust_domain_received_all_fragments:",
          tview["no_single_trust_domain_received_all_fragments"])
    for warning in _same_domain_warnings(tview):
        print(warning, file=sys.stderr)
    print("local-only fields never transmitted:",
          ", ".join(sorted(inputs["local_only"])) or "(none)")


def _confirm(yes: bool) -> bool:
    if yes:
        return True
    if not sys.stdin.isatty():
        print("\nRefusing to transmit: non-interactive session without --yes.",
              file=sys.stderr)
        return False
    return input("\nType 'send' to transmit these payloads, anything else aborts: ") == "send"


def _write_combined(out_dir: Path, inputs: dict, seats: dict,
                    responses: dict) -> Path:
    local_only = inputs["local_only"]
    parts = ["# Combined answer (assembled locally)\n"]
    for fid, adapter in seats.items():
        parts.append(f"\n## Fragment `{fid}` — {adapter.provider_id} "
                     f"(saw only its payload)\n")
        resp = responses.get(fid)
        parts.append((resp.text if resp else "(no response — provider call failed)") + "\n")
    parts.append("\n## Local-only context (reintroduced on this machine only)\n")
    for fld, value in sorted(local_only.items()):
        parts.append(f"- **{fld}**: {value}\n")
    combined = out_dir / "combined_answer.local.md"
    combined.write_text("".join(parts), encoding="utf-8")
    return combined


def run(example_dir: str, seat_specs: list[str] | None = None,
        output: str = "apl-live-out", yes: bool = False,
        transport: Transport | None = None, chain: str | None = None) -> int:
    paths = c.example_paths(example_dir)

    # 0. LOAD ONCE — every payload, local_only and masking_plan is read from
    # disk exactly here. The leak gate, preflight, wire, hashes and receipt
    # body all consume these same in-memory buffers: a file overwritten after
    # this point cannot make the receipt disagree with what was transmitted.
    inputs = c.load_run_inputs(paths)

    # 1. LEAK GATE — same rule as `apl mask`, enforced before any socket opens,
    # over the very buffers that will be transmitted.
    leaks = c.leak_findings_from_texts(inputs["local_only"], inputs["payloads"])
    if leaks:
        print("LEAK CHECK FAILED -- refusing to transmit:", file=sys.stderr)
        for leak in leaks:
            print(f"  ! {leak}", file=sys.stderr)
        return 1

    # 1b. CHAIN GATE — refuse to chain onto a receipt that does not verify.
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

    # 1c. SEAT RESOLUTION — named mapping, fail-close, zero transport on error.
    try:
        seats = resolve_seats(paths, seat_specs, transport)
    except ByokConfigError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2

    # 2. PRE-FLIGHT + consent (includes per-trust-domain aggregation).
    _preflight(paths, inputs, seats)
    if not _confirm(yes):
        print("Aborted. Nothing was transmitted.")
        return 1

    # 3. TRANSMIT.
    out_dir = Path(output)
    out_dir.mkdir(parents=True, exist_ok=True)
    responses: dict[str, object | None] = {}
    failures = []
    for fid, adapter in seats.items():
        payload = inputs["payloads"][fid]  # the single-read buffer, not a re-read
        try:
            result = adapter.complete(ProviderRequest(prompt=payload, model=adapter.model))
            responses[fid] = result
            (out_dir / f"live_answer_{fid}.local.txt").write_text(
                result.text, encoding="utf-8")
            print(f"[seat {fid}] live response received ({len(result.text)} chars)"
                  f" from {adapter.endpoint_host}")
            completion = result.metadata.get("completion", "unknown")
            if completion == "truncated":
                print(f"[seat {fid}] WARNING: provider truncated this response"
                      " at its length limit; the receipt records"
                      " response_truncated=true so a partial answer can never"
                      " masquerade as complete.", file=sys.stderr)
            elif completion == "unknown":
                reason = result.metadata.get("finish_reason",
                                             result.metadata.get("stop_reason"))
                print(f"[seat {fid}] WARNING: provider did not report a"
                      f" known-complete finish signal ({reason!r}); the"
                      " receipt records completion=\"unknown\" — treat this"
                      " answer as possibly incomplete.", file=sys.stderr)
        except TransportError as exc:
            responses[fid] = None
            failures.append(fid)
            print(f"[seat {fid}] FAILED: {exc}", file=sys.stderr)

    # 4. RECEIPT — signed and verified even for partial runs: what was
    # disclosed was disclosed, whether or not an answer came back.
    key, key_id = _signing.ensure_local_keypair()
    receipt = _signing.sign_receipt(
        build_receipt_body(paths, inputs, seats, responses, prev_hash), key, key_id)
    receipt_path = out_dir / "receipt.live.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")

    repo_root = c.REPO
    sys.path.insert(0, str(repo_root / "verifier"))
    import apl_verify  # noqa: E402
    apl_verify.verify_receipt(receipt)  # raises on any failure — fail-close

    combined = _write_combined(out_dir, inputs, seats, responses)
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
