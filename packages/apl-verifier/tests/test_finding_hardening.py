# SPDX-License-Identifier: Apache-2.0
"""Regression tests for two hardening findings surfaced in CoSAI ws4 #61.

A. Non-finite numbers (NaN / Infinity) must be rejected — they are not
   interoperable canonical JSON (RFC 8785 forbids them) and they silently
   defeat every `abs(claimed - recomputed) > tol` consistency check.
B. Provider-level headline claims must be re-derived from the signed data, not
   trusted from the emitter:
   B1. max_single_provider_exposure on the v0.1 path (no trust_domain_exposure)
       must equal max(single_provider_exposure ratios).
   B2. no_single_provider_saw_full must match the provider payload hashes vs
       original_task_sha256, when that field is present.

Each check runs before the signature check, so a tampered field is caught even
though tampering also breaks the signature — that is the point: an emitter with
its own key can produce an internally-signed receipt whose headline claims lie.
"""
import json
from pathlib import Path

import pytest

from apl_verifier import VerifyError, verify_receipt
from apl_verifier.receipt import canonical_bytes, load_receipt_json

_REPO = Path(__file__).resolve().parents[3]
_SPEC = _REPO / "src" / "apl_sidecar" / "spec"
_V01 = _SPEC / "conformance_vectors" / "valid_chain" / "receipt_001.json"
_WITH_ORIG = _REPO / "src" / "apl_sidecar" / "examples" / "00_private_matter" / "receipt.json"
_NONFINITE_VECTOR = (
    _SPEC / "conformance_vectors" / "tamper_vectors" / "tamper_nonfinite_exposure.json"
)
_ANY_PEM = str(_SPEC / "apl-oss-demo-key.pem")  # never reached: checks raise first


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


# --- Finding A -------------------------------------------------------------

@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
def test_load_rejects_nonfinite_literals(literal):
    with pytest.raises(ValueError, match="non-finite"):
        load_receipt_json('{"max_single_provider_exposure": %s}' % literal)


@pytest.mark.parametrize("value", ["1e400", "-1e400"])
def test_load_rejects_overflow_to_inf(value):
    """Syntactically valid exponent values that overflow to ±inf must be
    rejected at parse time, not accepted silently and caught later."""
    with pytest.raises(ValueError, match="non-finite"):
        load_receipt_json('{"exposure_ratio": %s}' % value)


def test_canonical_bytes_refuses_nan():
    with pytest.raises(ValueError):
        canonical_bytes({"exposure_ratio": float("nan")})


@pytest.mark.skipif(not _V01.is_file(), reason="spec vectors only in a checkout")
def test_verify_rejects_in_memory_nan_as_verifyerror():
    r = _load(_V01)
    r["max_single_provider_exposure"] = float("inf")
    with pytest.raises(VerifyError, match="non-finite"):
        verify_receipt(r, _ANY_PEM)


# --- Finding B1: v0.1 max_single_provider_exposure re-derived ---------------

@pytest.mark.skipif(not _V01.is_file(), reason="spec vectors only in a checkout")
def test_v01_max_provider_exposure_is_rederived():
    r = _load(_V01)
    assert "trust_domain_exposure" not in r  # v0.1 receipt
    real = max(x["exposure_ratio"] for x in r["single_provider_exposure"])
    r["max_single_provider_exposure"] = round(real / 2, 6)  # under-report the worst
    with pytest.raises(VerifyError, match="max_single_provider_exposure"):
        verify_receipt(r, _ANY_PEM)


# --- Finding B2: no_single_provider_saw_full re-derived when hashable --------

@pytest.mark.skipif(not _WITH_ORIG.is_file(), reason="spec vectors only in a checkout")
def test_saw_full_flag_is_rederived_when_original_hash_present():
    r = _load(_WITH_ORIG)
    assert "original_task_sha256" in r
    # flip the honest flag to the reassuring lie
    r["no_single_provider_saw_full"] = not r["no_single_provider_saw_full"]
    with pytest.raises(VerifyError, match="no_single_provider_saw_full"):
        verify_receipt(r, _ANY_PEM)


@pytest.mark.skipif(not _WITH_ORIG.is_file(), reason="spec vectors only in a checkout")
def test_saw_full_true_lie_caught_when_a_provider_saw_full():
    """A provider whose payload_sha256 == original_task_sha256 saw the full
    context; claiming no_single_provider_saw_full: true must be rejected."""
    r = _load(_WITH_ORIG)
    r["provider_events"][0]["payload_sha256"] = r["original_task_sha256"]
    r["no_single_provider_saw_full"] = True
    with pytest.raises(VerifyError, match="no_single_provider_saw_full"):
        verify_receipt(r, _ANY_PEM)


# --- Null provider_id bypass guard -------------------------------------------

def _minimal_receipt(**overrides):
    r = {
        "run_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
        "task_type": "test",
        "policy_id": "p1",
        "provider_events": [
            {"provider_id": "pA", "payload_sha256": "a" * 64, "event_type": "mock"}
        ],
        "local_only_hashes": [],
        "single_provider_exposure": [{"provider_id": "pA", "exposure_ratio": 0.5}],
        "max_single_provider_exposure": 0.5,
        "no_single_provider_saw_full": True,
        "prev_receipt_hash": None,
        "receipt_hash": "b" * 64,
        "signature": {"alg": "Ed25519", "value": "AAAA"},
        "signing_key_id": "k1",
        "masking_level": "guided_curated_p0",
        "provenance": {},
    }
    r.update(overrides)
    return r


def test_null_provider_id_in_events_is_rejected():
    """provider_events entry with provider_id: null must be caught; without
    an explicit null check the set-equality comparison collapses to {} == {}
    and a receipt claiming max_exposure: 0.0 can pass with real exposure omitted."""
    r = _minimal_receipt(
        provider_events=[{"provider_id": None, "payload_sha256": "a" * 64,
                          "event_type": "mock"}],
        single_provider_exposure=[],
        max_single_provider_exposure=0.0,
    )
    with pytest.raises(VerifyError, match="provider_id"):
        verify_receipt(r, _ANY_PEM)


def test_null_provider_id_in_exposure_is_rejected():
    r = _minimal_receipt(
        single_provider_exposure=[{"provider_id": None, "exposure_ratio": 0.5}],
    )
    with pytest.raises(VerifyError, match="provider_id"):
        verify_receipt(r, _ANY_PEM)


# --- Finding A: tamper vector is rejected specifically at parse boundary ------

@pytest.mark.skipif(
    not _NONFINITE_VECTOR.is_file(), reason="spec vectors only in a checkout"
)
def test_nonfinite_tamper_vector_rejected_at_parse_boundary():
    """The tamper_nonfinite_exposure.json vector carries `NaN` as a bare token.
    Passing its raw text through load_receipt_json must raise ValueError with
    "non-finite" — proving the parse-time finite-number guard caused the
    failure, attributably, rather than a pre-existing receipt_hash mismatch."""
    raw = _NONFINITE_VECTOR.read_text(encoding="utf-8")
    with pytest.raises(ValueError, match="non-finite"):
        load_receipt_json(raw)


# --- yc-oia PR #3 review 2: direct coverage for the shape-check guards --------
#
# Each guard below already exists in _check_shape; these lock the behaviour so a
# later refactor cannot silently drop it. All run before the signature check, so
# _ANY_PEM is never reached — the VerifyError is the whole assertion.

def test_mismatched_provider_id_sets_rejected():
    """A provider present in events but omitted from single_provider_exposure
    would be excluded from the recomputed max; the set-equality check catches it."""
    r = _minimal_receipt(
        provider_events=[{"provider_id": "pA", "payload_sha256": "a" * 64,
                          "event_type": "mock"}],
        single_provider_exposure=[{"provider_id": "pB", "exposure_ratio": 0.5}],
    )
    with pytest.raises(VerifyError, match="different provider_id sets"):
        verify_receipt(r, _ANY_PEM)


def test_negative_provider_exposure_ratio_rejected():
    r = _minimal_receipt(
        single_provider_exposure=[{"provider_id": "pA", "exposure_ratio": -0.5}],
    )
    with pytest.raises(VerifyError, match="non-negative"):
        verify_receipt(r, _ANY_PEM)


@pytest.mark.parametrize("bad,msg", [
    (True, "numeric"),          # bool is an int subclass — must not pass as numeric
    (-0.1, "non-negative"),
])
def test_bad_max_single_provider_exposure_rejected(bad, msg):
    r = _minimal_receipt(max_single_provider_exposure=bad)
    with pytest.raises(VerifyError, match=msg):
        verify_receipt(r, _ANY_PEM)


@pytest.mark.parametrize("bad", [1, 0, "true"])
def test_non_boolean_saw_full_rejected(bad):
    """no_single_provider_saw_full must be a JSON boolean; an integer 1/0 or a
    string must not be accepted as truthy."""
    r = _minimal_receipt(no_single_provider_saw_full=bad)
    with pytest.raises(VerifyError, match="must be a boolean"):
        verify_receipt(r, _ANY_PEM)


@pytest.mark.parametrize("bad", [
    int("1" * 64),      # 64-digit integer: the exact str()-coercion bypass
    "a" * 63,           # too short
    "a" * 65,           # too long
    "A" * 64,           # upper-hex is not lower-hex
    "g" * 64,           # non-hex character
    "a" * 64 + "\n",    # trailing newline slips past a bare `$` anchor
])
def test_invalid_original_task_sha256_rejected(bad):
    r = _minimal_receipt(original_task_sha256=bad)
    with pytest.raises(VerifyError, match="original_task_sha256"):
        verify_receipt(r, _ANY_PEM)


def test_integer_receipt_hash_rejected():
    """The same str()-coercion bypass closed for original_task_sha256 also
    applied to receipt_hash; a 64-digit integer must not masquerade as a digest."""
    r = _minimal_receipt(receipt_hash=int("1" * 64))
    with pytest.raises(VerifyError, match="receipt_hash"):
        verify_receipt(r, _ANY_PEM)
