"""APL receipt verifier — reference implementation of RECEIPT_STANDARD.md.

Standalone: verifies schema shape, canonical hash, Ed25519 signature, and
chain continuity. Fail-close: anything unexpected is a verification failure.

Usage:
    python verifier/apl_verify.py <receipt.json> [more_receipts_in_chain_order...]
                                  [--pubkey path.pem]

Exit codes: 0 = verified, 1 = failed, 2 = usage.
Dependency: cryptography (Ed25519).
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import sys
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

_HEX64 = re.compile(r"^[a-f0-9]{64}$")
_ULID = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")

REQUIRED_FIELDS = (
    "run_id", "task_type", "policy_id", "provider_events",
    "local_only_hashes", "single_provider_exposure",
    "max_single_provider_exposure", "no_single_provider_saw_full",
    "prev_receipt_hash", "receipt_hash", "signature", "signing_key_id",
    "masking_level", "provenance",
)

_REPO = Path(__file__).resolve().parents[1]
# pubkey resolution order for a given signing_key_id (first hit wins)
_KEY_DIRS = (_REPO / "keys", _REPO / "spec")

VALID_MESSAGE = "Signature verified. Receipt chain valid."
FAIL_MESSAGE = "Verification failed: receipt was modified or signature is invalid."


class VerifyError(Exception):
    """Deterministic verification failure with a human-readable reason."""


def canonical_bytes(obj) -> bytes:
    """Canonical JSON per RECEIPT_STANDARD.md section 2."""
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
    for ev in receipt["provider_events"]:
        if not _HEX64.match(str(ev.get("payload_sha256", ""))):
            raise VerifyError("provider_events payload_sha256 malformed")
    for h in receipt["local_only_hashes"]:
        if not _HEX64.match(str(h.get("sha256", ""))):
            raise VerifyError("local_only_hashes sha256 malformed")


def load_public_key(signing_key_id: str, pubkey_path: str | None = None) -> Ed25519PublicKey:
    if pubkey_path:
        candidates = [Path(pubkey_path)]
    else:
        candidates = [d / f"{signing_key_id}.pem" for d in _KEY_DIRS]
    for p in candidates:
        if p.exists():
            key = serialization.load_pem_public_key(p.read_bytes())
            if not isinstance(key, Ed25519PublicKey):
                raise VerifyError(f"not an Ed25519 public key: {p}")
            return key
    raise VerifyError(
        f"no public key found for signing_key_id={signing_key_id!r} "
        f"(searched: {', '.join(str(c) for c in candidates)})")


def _check_trust_domain_consistency(receipt: dict) -> None:
    """v0.2 additive fields: when present, the per-trust-domain aggregation
    must be recomputable from the signed per-seat data. Absent fields (v0.1
    receipts) skip this check entirely — backward compatible by design."""
    tde = receipt.get("trust_domain_exposure")
    if tde is None:
        return
    seat_ratio = {e["provider_id"]: e["exposure_ratio"]
                  for e in receipt.get("single_provider_exposure", [])}
    seat_domain = {ev.get("seat_id"): ev.get("trust_domain")
                   for ev in receipt.get("provider_events", [])}
    seat_by_id = {ev.get("seat_id"): ev.get("provider_id")
                  for ev in receipt.get("provider_events", [])}
    recomputed: dict[str, float] = {}
    for seat_id, domain in seat_domain.items():
        if seat_id is None or domain is None:
            raise VerifyError("trust_domain_exposure present but an event lacks "
                              "seat_id/trust_domain")
        ratio = seat_ratio.get(seat_by_id[seat_id])
        if ratio is None:
            raise VerifyError(f"no per-seat exposure recorded for seat {seat_id!r}")
        recomputed[domain] = round(recomputed.get(domain, 0.0) + ratio, 6)
    claimed = {d["trust_domain"]: d["exposure_ratio"] for d in tde}
    if set(claimed) != set(recomputed):
        raise VerifyError("trust_domain_exposure domains do not match events")
    for domain, ratio in claimed.items():
        if abs(ratio - recomputed[domain]) > 1e-6:
            raise VerifyError(
                f"trust_domain_exposure for {domain!r} is {ratio}, recomputed "
                f"{recomputed[domain]} from signed per-seat data")
    for field, value in (
            ("max_single_trust_domain_exposure",
             round(max(recomputed.values(), default=0.0), 6)),
            ("max_single_provider_exposure",
             round(max(recomputed.values(), default=0.0), 6))):
        if field in receipt and abs(receipt[field] - value) > 1e-6:
            raise VerifyError(f"{field} is {receipt[field]}, recomputed {value}")


def verify_receipt(receipt: dict, pubkey_path: str | None = None) -> None:
    """Raises VerifyError on any failure; returns None when valid."""
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


def verify_chain(receipts: list[dict], pubkey_path: str | None = None) -> None:
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


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    pubkey = None
    if "--pubkey" in argv:
        i = argv.index("--pubkey")
        try:
            pubkey = argv[i + 1]
        except IndexError:
            print("usage: apl_verify.py <receipt.json>... [--pubkey key.pem]")
            return 2
        del argv[i:i + 2]
    if not argv:
        print("usage: apl_verify.py <receipt.json>... [--pubkey key.pem]")
        return 2
    receipts = []
    for path in argv:
        try:
            receipts.append(json.loads(Path(path).read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            print(f"{FAIL_MESSAGE} ({path}: {exc})")
            return 1
    try:
        verify_chain(receipts, pubkey)
    except VerifyError as exc:
        print(f"{FAIL_MESSAGE} ({exc})")
        return 1
    print(VALID_MESSAGE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
