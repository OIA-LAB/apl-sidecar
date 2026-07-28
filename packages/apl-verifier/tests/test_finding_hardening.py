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
_ANY_PEM = str(_SPEC / "apl-oss-demo-key.pem")  # never reached: checks raise first


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


# --- Finding A -------------------------------------------------------------

@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
def test_load_rejects_nonfinite_literals(literal):
    with pytest.raises(ValueError):
        load_receipt_json('{"max_single_provider_exposure": %s}' % literal)


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
