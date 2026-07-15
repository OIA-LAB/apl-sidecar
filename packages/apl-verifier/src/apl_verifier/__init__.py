# SPDX-License-Identifier: Apache-2.0
"""apl-verifier — the independent, permanently Apache-2.0 verification layer.

This package contains ONLY verification capability: receipt schema constants,
canonical serialization, hash, Ed25519 signature and chain verification, the
single trust-domain normalization rule, and interface-only plugin Protocols.
It has no dependency on the APL runtime (dependency direction is one-way:
runtime -> apl-verifier). It performs no planning, no automatic decomposition,
no provider transport.

Licensing: this package is and will remain Apache-2.0. See LICENSE / NOTICE.
"""
from __future__ import annotations

from .receipt import (
    FAIL_MESSAGE,
    REQUIRED_FIELDS,
    VALID_MESSAGE,
    VerifyError,
    canonical_bytes,
    compute_receipt_hash,
    load_public_key,
    verify_chain,
    verify_receipt,
)
from .trust import VENDOR_TRUST_DOMAINS, normalize_host, trust_domain

__version__ = "0.2.0"

__all__ = [
    "FAIL_MESSAGE",
    "REQUIRED_FIELDS",
    "VALID_MESSAGE",
    "VerifyError",
    "canonical_bytes",
    "compute_receipt_hash",
    "load_public_key",
    "verify_chain",
    "verify_receipt",
    "VENDOR_TRUST_DOMAINS",
    "normalize_host",
    "trust_domain",
    "__version__",
]
