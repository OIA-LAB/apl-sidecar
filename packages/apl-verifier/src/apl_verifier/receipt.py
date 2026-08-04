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
import math
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


def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    """`object_pairs_hook` that fails-close on a repeated JSON object member.

    Plain `json.loads` keeps the LAST value for a duplicated key and silently
    drops the rest. That is a tamper channel: a receipt could carry a duplicate
    `receipt_hash`/`signature`/field so that a naive reader (or a second parser)
    sees a different value than the one this verifier hashes and checks. RFC
    8259 says names within an object SHOULD be unique and the behaviour of
    duplicate names is unpredictable -- a signed security receipt must reject
    them, not gamble. Raises ValueError so both CLI read sites, which already
    wrap parsing in `except (OSError, ValueError)`, fail-close to exit 1.
    """
    seen: set[str] = set()
    for key, _ in pairs:
        if key in seen:
            raise ValueError(f"duplicate JSON object key {key!r} -- a receipt "
                             "must not repeat a member (fail-close)")
        seen.add(key)
    return dict(pairs)


def _reject_nonfinite_literal(token: str):
    """`parse_constant` hook that fails-close on the non-finite JSON literals.

    Plain `json.loads` accepts the bare tokens `NaN`, `Infinity` and
    `-Infinity` (a CPython extension), and plain `json.dumps` re-emits them
    verbatim. That is a canonicalisation hole: a receipt could carry
    `"max_single_provider_exposure": NaN`, hash and sign stably under
    apl-json-v1, yet be unparseable by a strict JSON / RFC 8785 verifier
    (which forbids non-finite numbers) -- so it would not be independently
    verifiable, and any `abs(claimed - recomputed) > tol` consistency check
    silently accepts it because every comparison with NaN is False. Receipts
    must contain only finite numbers; reject at parse. Raises ValueError so the
    CLI read sites (which wrap parsing in `except (OSError, ValueError)`)
    fail-close to exit 1."""
    raise ValueError(f"non-finite JSON number {token!r} -- a receipt must "
                     "contain only finite numbers (fail-close)")


def _finite_float(s: str) -> float:
    """`parse_float` hook that fails-close on numeric values that overflow to
    a non-finite float, such as `1e400` → `inf`.

    `parse_constant` only catches the bare tokens `NaN`, `Infinity`, and
    `-Infinity`. Syntactically valid exponent notation that overflows
    (e.g. `1e400`, `-1e400`) passes through `parse_constant` unnoticed and
    silently becomes `math.inf` or `-math.inf`. The fix: replace the float
    conversion with one that raises ValueError on a non-finite result, so the
    same CLI fail-close path applies. This also keeps the parse and the
    `allow_nan=False` serialisation guard consistent for out-of-range inputs."""
    value = float(s)
    if not math.isfinite(value):
        raise ValueError(
            f"non-finite numeric value {s!r} (overflows to infinity) -- a "
            "receipt must contain only finite numbers (fail-close)")
    return value


def load_receipt_json(text: str) -> dict:
    """Parse one receipt from JSON text, rejecting duplicate object keys and
    non-finite numbers.

    The single parse entry point for receipts: every read site must route
    through here so the strict duplicate-key and finite-number rules are
    enforced uniformly. Same return value as `json.loads` for well-formed
    input; raises ValueError (json.JSONDecodeError is a ValueError, as are the
    duplicate-key and non-finite errors) on any malformed, duplicate-key or
    non-finite input."""
    return json.loads(text, object_pairs_hook=_no_duplicate_keys,
                      parse_constant=_reject_nonfinite_literal,
                      parse_float=_finite_float)


def canonical_bytes(obj) -> bytes:
    """Canonical JSON per the receipt standard (section 2).

    `allow_nan=False`: apl-json-v1 admits only finite numbers, matching RFC
    8785. Defence in depth alongside the parse-time `parse_constant` guard, so
    a NaN/Infinity reaching this function via the in-memory API (not the JSON
    parser) raises ValueError rather than emitting a non-interoperable token."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def compute_receipt_hash(receipt: dict) -> str:
    body = {k: v for k, v in receipt.items()
            if k not in ("receipt_hash", "signature")}
    return hashlib.sha256(canonical_bytes(body)).hexdigest()


def _reject_nonfinite_numbers(obj, path: str = "receipt") -> None:
    """Fail-close on any non-finite float anywhere in an in-memory receipt.

    The parse-time `parse_constant` guard covers receipts read from JSON text;
    this covers the library API where `verify_receipt(dict)` is called with a
    dict built in memory, so a NaN/Infinity raises a clean VerifyError instead
    of a raw ValueError escaping from `canonical_bytes`."""
    if isinstance(obj, float) and not math.isfinite(obj):
        raise VerifyError(f"non-finite number at {path} -- a receipt must "
                          "contain only finite numbers")
    if isinstance(obj, dict):
        for k, v in obj.items():
            _reject_nonfinite_numbers(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _reject_nonfinite_numbers(v, f"{path}[{i}]")


def _is_hex64(value: object) -> bool:
    """True only for a ``str`` that is exactly 64 lower-hex characters.

    Enforcing the ``str`` type is the point. ``_HEX64.match(str(value))``
    stringifies first, so a 64-digit *integer* renders to 64 digit-chars
    and slips through -- a numeric ``original_task_sha256`` / ``receipt_hash``
    would masquerade as a valid digest. A digest is textual; anything that is
    not a ``str`` is malformed by construction.

    ``fullmatch`` (not ``match``) closes a second gap: the ``$`` anchor in
    ``_HEX64`` also matches immediately before a trailing newline, so
    ``"<64hex>\\n"`` would otherwise pass. ``fullmatch`` requires the whole
    string, newline included, to be hex.
    """
    return isinstance(value, str) and _HEX64.fullmatch(value) is not None


def _check_shape(receipt: dict) -> None:
    _reject_nonfinite_numbers(receipt)
    missing = [f for f in REQUIRED_FIELDS if f not in receipt]
    if missing:
        raise VerifyError(f"missing required fields: {', '.join(missing)}")
    if not _ULID.match(str(receipt["run_id"])):
        raise VerifyError("run_id is not a ULID")
    if not _is_hex64(receipt["receipt_hash"]):
        raise VerifyError("receipt_hash is not 64 lower-hex chars")
    prev = receipt["prev_receipt_hash"]
    if prev is not None and not _is_hex64(prev):
        raise VerifyError("prev_receipt_hash is neither null nor 64 lower-hex")
    sig = receipt["signature"]
    if not isinstance(sig, dict) or sig.get("alg") != "Ed25519" or not sig.get("value"):
        raise VerifyError("signature must be {alg: 'Ed25519', value: <base64>}")
    if not _KEY_ID.match(str(receipt["signing_key_id"])):
        raise VerifyError("signing_key_id must match [A-Za-z0-9._-]{1,64} "
                          "(no path separators)")
    if not isinstance(receipt["no_single_provider_saw_full"], bool):
        raise VerifyError(
            "no_single_provider_saw_full must be a boolean, not "
            f"{type(receipt['no_single_provider_saw_full']).__name__!r}")
    msp = receipt["max_single_provider_exposure"]
    if not isinstance(msp, (int, float)) or isinstance(msp, bool):
        raise VerifyError("max_single_provider_exposure must be numeric")
    if msp < 0:
        raise VerifyError(
            f"max_single_provider_exposure must be non-negative (got {msp})")
    orig_sha = receipt.get("original_task_sha256")
    if orig_sha is not None and not _is_hex64(orig_sha):
        raise VerifyError("original_task_sha256 must be 64 lower-hex chars")
    for ev in receipt["provider_events"]:
        if not _is_hex64(ev.get("payload_sha256")):
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
        if not _is_hex64(h.get("sha256")):
            raise VerifyError("local_only_hashes sha256 malformed")
    # Every provider_events entry must carry a non-null provider_id; null is
    # excluded from the set-equality check below (by design, to avoid
    # crashing on malformed input), so a receipt where all entries have
    # provider_id: null would pass the set check with an empty
    # single_provider_exposure and a claimed max of 0.0. Reject null
    # provider_ids explicitly so the exclusion never becomes a bypass.
    for e in receipt["provider_events"]:
        if e.get("provider_id") is None:
            raise VerifyError("provider_events entry missing provider_id")
    for x in receipt["single_provider_exposure"]:
        if x.get("provider_id") is None:
            raise VerifyError("single_provider_exposure entry missing provider_id")
    # Duplicates fail-close: dict aggregation downstream would silently
    # collapse repeated ids and let one seat's exposure hide behind another's.
    _reject_duplicates("provider_events provider_id",
                       [e.get("provider_id") for e in receipt["provider_events"]])
    _reject_duplicates("provider_events seat_id",
                       [e["seat_id"] for e in receipt["provider_events"]
                        if "seat_id" in e])
    for x in receipt["single_provider_exposure"]:
        if not isinstance(x.get("exposure_ratio"), (int, float)) \
                or isinstance(x.get("exposure_ratio"), bool):
            raise VerifyError("single_provider_exposure entry lacks a numeric "
                              "exposure_ratio")
        if x["exposure_ratio"] < 0:
            raise VerifyError(
                "single_provider_exposure exposure_ratio must be non-negative "
                f"(got {x['exposure_ratio']})")
    _reject_duplicates("single_provider_exposure provider_id",
                       [x.get("provider_id")
                        for x in receipt["single_provider_exposure"]])
    _reject_duplicates("trust_domain_exposure trust_domain",
                       [d.get("trust_domain")
                        for d in receipt.get("trust_domain_exposure") or []])
    # provider_ids in provider_events and single_provider_exposure must be the
    # same set. A provider omitted from single_provider_exposure would be
    # excluded from the recomputed max, so a malicious emitter could claim a
    # lower max_single_provider_exposure than the true maximum.
    event_ids = (
        {e.get("provider_id") for e in receipt["provider_events"]} - {None}
    )
    exposure_ids = (
        {x.get("provider_id") for x in receipt["single_provider_exposure"]}
        - {None}
    )
    if event_ids != exposure_ids:
        only_events = sorted(event_ids - exposure_ids)
        only_exposure = sorted(exposure_ids - event_ids)
        raise VerifyError(
            "provider_events and single_provider_exposure have different "
            f"provider_id sets; only in events: {only_events}, only in "
            f"exposure: {only_exposure}")


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
    # In the n-way model a "provider" is a trust domain, so BOTH
    # max_single_trust_domain_exposure and max_single_provider_exposure equal
    # the largest per-domain aggregate here. (single_provider_exposure carries
    # the per-SEAT ratios in this model; its max is max_single_seat_exposure,
    # checked in _check_max_single_seat.)
    for field in ("max_single_trust_domain_exposure", "max_single_provider_exposure"):
        value = round(max(recomputed.values(), default=0.0), 6)
        if field in receipt and abs(receipt[field] - value) > 1e-6:
            raise VerifyError(f"{field} is {receipt[field]}, recomputed {value}")
    # (c) max_single_seat_exposure, from the per-seat ratios.
    _check_max_single_seat(receipt, events, seat_ratio)


def _check_provider_headline(receipt: dict) -> None:
    """Re-derive the provider-level headline claims from the signed data. The
    exposure model (docs/exposure_model.md) states these are 'recomputable from
    the receipt by anyone', but before this the verifier only re-derived the
    trust-domain aggregates — so a v0.1 receipt (no trust_domain_exposure) could
    carry a max / 'no provider saw full' claim its own signed data contradicts
    and still verify.

      - max_single_provider_exposure: on the v0.1 path (no trust_domain_exposure)
        single_provider_exposure is genuinely per-provider, so the claim must
        equal round(max(exposure_ratio), 6). On the v0.2 (n-way) path a provider
        is a trust domain and this field is the per-domain aggregate, already
        re-derived in _check_trust_domain_consistency — so skip it here to avoid
        conflating the per-domain aggregate with the per-seat max.
      - no_single_provider_saw_full == not any(payload_sha256 == original_task_sha256),
        checked on any path but only when original_task_sha256 is present — it is
        the only signed field that reproduces the producer's `payload == original`
        test; a ratio-only shortcut would false-reject a same-length,
        different-content payload. Making original_task_sha256 a required signed
        field in a future receipt version would let this run unconditionally.

    Scope of the original_task_sha256 check: this establishes internal
    consistency AMONG the signed receipt fields — that the emitter's own
    payload hashes agree with its own no_single_provider_saw_full flag. It
    does NOT prove the emitter supplied the true hash of the original task; a
    colluding emitter controls both fields and can sign a receipt where both
    lie in concert. Independent verification of the original input requires an
    out-of-band reference hash held by the requester.
    """
    if receipt.get("trust_domain_exposure") is None \
            and "max_single_provider_exposure" in receipt:
        ratios = [x["exposure_ratio"] for x in receipt["single_provider_exposure"]]
        expected = round(max(ratios, default=0.0), 6)
        if abs(receipt["max_single_provider_exposure"] - expected) > 1e-6:
            raise VerifyError(
                f"max_single_provider_exposure is "
                f"{receipt['max_single_provider_exposure']}, recomputed "
                f"{expected} from single_provider_exposure")
    orig = receipt.get("original_task_sha256")
    if orig is not None and "no_single_provider_saw_full" in receipt:
        saw_full = any(ev.get("payload_sha256") == orig
                       for ev in receipt["provider_events"])
        if receipt["no_single_provider_saw_full"] != (not saw_full):
            raise VerifyError(
                "no_single_provider_saw_full is "
                f"{receipt['no_single_provider_saw_full']}, recomputed "
                f"{not saw_full} from provider payload_sha256 vs "
                "original_task_sha256")


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
    _check_provider_headline(receipt)
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
