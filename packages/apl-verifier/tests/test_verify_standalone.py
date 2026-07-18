# SPDX-License-Identifier: Apache-2.0
"""Standalone verifier tests over a synthetic, Apache-licensed fixture.

These do not touch the CC BY conformance vectors: the fixture receipt and key
are generated here at runtime, so this package is self-contained and its wheel
never needs to bundle spec vectors. A valid receipt verifies; a tampered copy
is rejected; a bad signing_key_id is rejected before any filesystem access.
"""
import base64

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from apl_verifier import VerifyError, compute_receipt_hash, verify_receipt


def _synthetic_receipt(private_key, key_id):
    body = {
        "run_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
        "task_type": "demo",
        "policy_id": "synthetic",
        "provider_events": [
            {"provider_id": "seat_a", "payload_sha256": "a" * 64},
            {"provider_id": "seat_b", "payload_sha256": "b" * 64},
        ],
        "local_only_hashes": [{"sha256": "c" * 64}],
        "single_provider_exposure": [
            {"provider_id": "seat_a", "exposure_ratio": 0.5},
            {"provider_id": "seat_b", "exposure_ratio": 0.5},
        ],
        "max_single_provider_exposure": 0.5,
        "no_single_provider_saw_full": True,
        "prev_receipt_hash": None,
        "signing_key_id": key_id,
        "masking_level": "demo",
        "provenance": {"source": "synthetic-apache-fixture"},
    }
    receipt_hash = compute_receipt_hash(body)
    sig = private_key.sign(receipt_hash.encode("utf-8"))
    body["receipt_hash"] = receipt_hash
    body["signature"] = {"alg": "Ed25519",
                         "value": base64.b64encode(sig).decode("ascii")}
    return body


@pytest.fixture()
def keyed(tmp_path):
    key = Ed25519PrivateKey.generate()
    pub = tmp_path / "syn.pem"
    pub.write_bytes(key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo))
    return key, "syn", str(pub)


def test_valid_receipt_verifies(keyed):
    key, key_id, pub = keyed
    verify_receipt(_synthetic_receipt(key, key_id), pub)  # must not raise


def test_tampered_receipt_rejected(keyed):
    key, key_id, pub = keyed
    receipt = _synthetic_receipt(key, key_id)
    receipt["provenance"]["source"] = "tampered"
    with pytest.raises(VerifyError):
        verify_receipt(receipt, pub)


def test_missing_pubkey_is_error(keyed):
    key, key_id, _pub = keyed
    with pytest.raises(VerifyError):
        verify_receipt(_synthetic_receipt(key, key_id), "")


def test_bad_key_id_rejected_before_fs(keyed):
    key, _key_id, pub = keyed
    receipt = _synthetic_receipt(key, "../../etc/passwd")
    with pytest.raises(VerifyError, match="signing_key_id"):
        verify_receipt(receipt, pub)
