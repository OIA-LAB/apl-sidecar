"""Local demo signing for APL Sidecar. Private keys never leave keys/ (gitignored)."""
from __future__ import annotations

import base64
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "verifier"))
from apl_verify import compute_receipt_hash  # noqa: E402

LOCAL_KEY_ID = "apl-local-demo-key"
KEYS_DIR = REPO / "keys"


def ensure_local_keypair() -> tuple[Ed25519PrivateKey, str]:
    """Create (once) and load a local demo keypair under gitignored keys/."""
    KEYS_DIR.mkdir(exist_ok=True)
    priv_path = KEYS_DIR / f"{LOCAL_KEY_ID}.private.pem"
    pub_path = KEYS_DIR / f"{LOCAL_KEY_ID}.pem"
    if priv_path.exists():
        key = serialization.load_pem_private_key(priv_path.read_bytes(), password=None)
    else:
        key = Ed25519PrivateKey.generate()
        priv_path.write_bytes(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()))
        pub_path.write_bytes(key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo))
    return key, LOCAL_KEY_ID


def sign_receipt(body: dict, private_key: Ed25519PrivateKey,
                 signing_key_id: str) -> dict:
    """body (no receipt_hash/signature) -> signed receipt per the standard."""
    receipt = dict(body)
    receipt["signing_key_id"] = signing_key_id
    receipt.pop("receipt_hash", None)
    receipt.pop("signature", None)
    receipt_hash = compute_receipt_hash(receipt)
    sig = private_key.sign(receipt_hash.encode("utf-8"))
    receipt["receipt_hash"] = receipt_hash
    receipt["signature"] = {"alg": "Ed25519",
                            "value": base64.b64encode(sig).decode("ascii")}
    return receipt
