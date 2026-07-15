# SPDX-License-Identifier: Apache-2.0
"""APL receipt verifier — reference implementation of the receipt standard.

Standalone and self-contained: verifies schema shape, canonical hash, Ed25519
signature, and chain continuity. Fail-close: anything unexpected is a
verification failure. The trust-domain rule is imported from
`apl_verifier.trust` (single implementation, no duplicated copy).

Public-key resolution is explicit only: a caller passes the PEM path. This
package never searches repo-relative `keys/` or `spec/` directories, so a
receipt can never steer the verifier at a filesystem path and an installed
verifier has no hidden dependency on any host layout.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .trust import trust_domain as _trust_domain

_HEX64 = re.compile(r"^[a-f0-9]{64}$")
_ULID = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")
# signing_key_id becomes a filename component in load_public_key: a strict
# allowlist (no separators, no traversal) so a receipt can never direct the
# verifier to read an attacker-chosen filesystem path.
_KEY_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")

REQUIRED_FIELDS = (
    "run_id", "task_type", "policy_id", "provider_events",
    "local_only_hashes", "single_provider_exposure",
    "max_single_provider_exposure", "no_single_provider_saw_full",
    "prev_receipt_hash", "receipt_hash", "signature", "signing_key_id",
    "masking_level", "provenance",
)

VALID_MESSAGE = "Signature verified. Receipt chain valid."
FAIL_MESSAGE = "Verification failed: receipt was modified or signature is invalid."


class VerifyError(Exception):
    """Deterministic verification failure with a human-readable reason."""


def canonical_bytes(obj) -> bytes:
    """Canonical JSON per the receipt standard (section 2)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def compute_receipt_hash(receipt: dict) -> str:
    body = {k: v for k, v in receipt.items()
            if k not in ("receipt_hash", "signature")}
    return hashlib.sha256(canonical_bytes(body)).hexdigest()


def _check_shape(receipt: dict) -> None:
    missing = [f for f in REQUIRED_FIELDS if f not in receipt]
    if missing:
        raise VerifyError(f"missing required fields: {', '.join(missing)}")
    if not _ULID.match(str(receipt["run_id"])):
        raise VerifyError("run_id is not a ULID")
    if not _HEX64.match(str(receipt["receipt_hash"])):
        raise VerifyError("receipt_hash is not 64 lower-hex chars")
    prev = receipt["prev_receipt_hash"]
    if prev is not None and not _HEX64.match(str(prev)):
        raise VerifyError("prev_receipt_hash is neither null nor 64 lower-hex")
    sig = receipt["signature"]
    if not isinstance(sig, dict) or sig.get("alg") != "Ed25519" or not sig.get("value"):
        raise VerifyError("signature must be {alg: 'Ed25519', value: <base64>}")
    if not _KEY_ID.match(str(receipt["signing_key_id"])):
        raise VerifyError("signing_key_id must match [A-Za-z0-9._-]{1,64} "
                          "(no path separators)")
    for ev in receipt["provider_events"]:
        if not _HEX64.match(str(ev.get("payload_sha256", ""))):
            raise VerifyError("provider_events payload_sha256 malformed")
        # completion (v0.2 additive) and the legacy boolean must agree.
        if "completion" in ev:
            if ev["completion"] not in ("complete", "truncated", "unknown"):
                raise VerifyError(f"completion {ev['completion']!r} is not one "
                                  "of complete/truncated/unknown")
            if "response_truncated" in ev and \
                    ev["response_truncated"] != (ev["completion"] == "truncated"):
                raise VerifyError("response_truncated contradicts completion")
    for h in receipt["local_only_hashes"]:
        if not _HEX64.match(str(h.get("sha256", ""))):
            raise VerifyError("local_only_hashes sha256 malformed")
    # Duplicates fail-close: dict aggregation downstream would silently
    # collapse repeated ids and let one seat's exposure hide behind another's.
    _reject_duplicates("provider_events provider_id",
                       [e.get("provider_id") for e in receipt["provider_events"]])
    _reject_duplicates("provider_events seat_id",
                       [e["seat_id"] for e in receipt["provider_events"]
                        if "seat_id" in e])
    _reject_duplicates("single_provider_exposure provider_id",
                       [x.get("provider_id")
                        for x in receipt["single_provider_exposure"]])
    _reject_duplicates("trust_domain_exposure trust_domain",
                       [d.get("trust_domain")
                        for d in receipt.get("trust_domain_exposure") or []])


def _reject_duplicates(label: str, values: list) -> None:
    if len(values) != len(set(values)):
        raise VerifyError(f"duplicate {label} — receipts must not repeat ids")


def load_public_key(signing_key_id: str, pubkey_path: str) -> Ed25519PublicKey:
    """Load the Ed25519 public key from an explicit PEM path.

    `pubkey_path` is REQUIRED. This package performs no directory search: the
    caller decides which key to trust. `signing_key_id` is still validated
    against the strict allowlist so malformed ids fail-close, but it is never
    used to build a filesystem path here.
    """
    if not _KEY_ID.match(str(signing_key_id)):
        raise VerifyError("signing_key_id must match [A-Za-z0-9._-]{1,64} "
                          "(no path separators)")
    if not pubkey_path:
        raise VerifyError("a public key path is required (--pubkey)")
    p = Path(pubkey_path)
    if not p.exists():
        raise VerifyError(f"public key not found: {p}")
    key = serialization.load_pem_public_key(p.read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise VerifyError(f"not an Ed25519 public key: {p}")
    return key


def _check_trust_domain_consistency(receipt: dict) -> None:
    """v0.2 additive fields: when present, the per-trust-domain aggregation
    must be recomputable from the signed per-seat data — a receipt cannot
    declare a trust domain, a seat set, or an aggregate that its own signed
    events do not support. Absent fields (v0.1 receipts) skip the check that
    references them — backward compatible by design.

    Re-derived here, each guarded by field presence so legacy mock receipts
    that lack endpoint_host / trust_domain / seat_ids still verify:
      0. per-event trust_domain, from endpoint_host via the SAME rule the
         runtime uses (apl_verifier.trust.trust_domain); declared != recomputed
         -> fail;
      a. trust_domain_exposure[].seat_ids == the actual seats per domain;
      b. no_single_trust_domain_received_all_fragments, from the seat sets;
      c. max_single_seat_exposure, from the per-seat ratios.
    """
    events = receipt.get("provider_events", [])
    seat_ratio = {e["provider_id"]: e["exposure_ratio"]
                  for e in receipt.get("single_provider_exposure", [])}

    # (0) endpoint_host -> trust_domain must match the declared trust_domain.
    # Only enforced for events that actually carry endpoint_host (v0.2+).
    for ev in events:
        host = ev.get("endpoint_host")
        declared = ev.get("trust_domain")
        if host is None or declared is None:
            continue
        recomputed_domain = _trust_domain(str(host))
        if declared != recomputed_domain:
            raise VerifyError(
                f"provider_events trust_domain {declared!r} does not match "
                f"{recomputed_domain!r} recomputed from endpoint_host "
                f"{host!r}")

    tde = receipt.get("trust_domain_exposure")
    if tde is None:
        # No per-domain aggregation to re-derive. The max_single_seat_exposure
        # field, if present, is still checkable against per-seat data below.
        _check_max_single_seat(receipt, events, seat_ratio)
        return

    seat_domain = {ev.get("seat_id"): ev.get("trust_domain") for ev in events}
    seat_by_id = {ev.get("seat_id"): ev.get("provider_id") for ev in events}
    recomputed: dict[str, float] = {}
    recomputed_seats: dict[str, list[str]] = {}
    for seat_id, domain in seat_domain.items():
        if seat_id is None or domain is None:
            raise VerifyError("trust_domain_exposure present but an event lacks "
                              "seat_id/trust_domain")
        ratio = seat_ratio.get(seat_by_id[seat_id])
        if ratio is None:
            raise VerifyError(f"no per-seat exposure recorded for seat {seat_id!r}")
        recomputed[domain] = round(recomputed.get(domain, 0.0) + ratio, 6)
        recomputed_seats.setdefault(domain, []).append(seat_id)
    claimed = {d["trust_domain"]: d["exposure_ratio"] for d in tde}
    if set(claimed) != set(recomputed):
        raise VerifyError("trust_domain_exposure domains do not match events")
    for domain, ratio in claimed.items():
        if abs(ratio - recomputed[domain]) > 1e-6:
            raise VerifyError(
                f"trust_domain_exposure for {domain!r} is {ratio}, recomputed "
                f"{recomputed[domain]} from signed per-seat data")
    # (a) declared seat_ids per domain must equal the actual seat sets.
    for d in tde:
        if "seat_ids" not in d:
            continue
        domain = d["trust_domain"]
        if set(d["seat_ids"]) != set(recomputed_seats.get(domain, [])):
            raise VerifyError(
                f"trust_domain_exposure seat_ids for {domain!r} do not match "
                f"the seats recorded in provider_events")
    # (b) no_single_trust_domain_received_all_fragments, from the seat sets.
    if "no_single_trust_domain_received_all_fragments" in receipt:
        all_seats = {sid for sid in seat_domain if sid is not None}
        recomputed_flag = not any(
            set(seats) == all_seats for seats in recomputed_seats.values())
        if receipt["no_single_trust_domain_received_all_fragments"] != recomputed_flag:
            raise VerifyError(
                "no_single_trust_domain_received_all_fragments is "
                f"{receipt['no_single_trust_domain_received_all_fragments']}, "
                f"recomputed {recomputed_flag} from the signed seat sets")
    for field in ("max_single_trust_domain_exposure", "max_single_provider_exposure"):
        value = round(max(recomputed.values(), default=0.0), 6)
        if field in receipt and abs(receipt[field] - value) > 1e-6:
            raise VerifyError(f"{field} is {receipt[field]}, recomputed {value}")
    # (c) max_single_seat_exposure, from the per-seat ratios.
    _check_max_single_seat(receipt, events, seat_ratio)


def _check_max_single_seat(receipt: dict, events: list, seat_ratio: dict) -> None:
    """max_single_seat_exposure (when present) must equal the largest per-seat
    exposure recorded in single_provider_exposure. Guarded by field presence
    so v0.1 receipts without this field are untouched."""
    if "max_single_seat_exposure" not in receipt:
        return
    if not seat_ratio:
        raise VerifyError("max_single_seat_exposure present but no per-seat "
                          "exposure recorded")
    value = round(max(seat_ratio.values(), default=0.0), 6)
    if abs(receipt["max_single_seat_exposure"] - value) > 1e-6:
        raise VerifyError(
            f"max_single_seat_exposure is {receipt['max_single_seat_exposure']}, "
            f"recomputed {value} from per-seat exposure")


def verify_receipt(receipt: dict, pubkey_path: str) -> None:
    """Raises VerifyError on any failure; returns None when valid.

    `pubkey_path` is required — the caller supplies the public key to trust.
    """
    _check_shape(receipt)
    _check_trust_domain_consistency(receipt)
    recomputed = compute_receipt_hash(receipt)
    if recomputed != receipt["receipt_hash"]:
        raise VerifyError("receipt_hash mismatch (content was modified)")
    key = load_public_key(receipt["signing_key_id"], pubkey_path)
    try:
        sig = base64.b64decode(receipt["signature"]["value"].encode("ascii"),
                               validate=True)
    except Exception as exc:
        raise VerifyError(f"signature is not valid base64: {exc}") from exc
    try:
        key.verify(sig, receipt["receipt_hash"].encode("utf-8"))
    except InvalidSignature:
        raise VerifyError("Ed25519 signature invalid") from None


def verify_chain(receipts: list[dict], pubkey_path: str) -> None:
    """Verify each receipt AND the prev_receipt_hash linkage, in order."""
    prev_hash = None
    for i, receipt in enumerate(receipts):
        try:
            verify_receipt(receipt, pubkey_path)
        except VerifyError as exc:
            raise VerifyError(f"receipt[{i}] invalid: {exc}") from exc
        if i == 0:
            prev_hash = receipt["receipt_hash"]
            continue
        if receipt["prev_receipt_hash"] != prev_hash:
            raise VerifyError(
                f"chain broken at index {i}: prev_receipt_hash does not match "
                f"receipt[{i - 1}].receipt_hash")
        prev_hash = receipt["receipt_hash"]
