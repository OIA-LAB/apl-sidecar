# SPDX-License-Identifier: Apache-2.0
"""Hard gate: apl-verifier 0.2.0 must verify a REAL v0.1.0 receipt and reject
its tampered twin, using the v0.1.0 demo public key.

The frozen pair lives at spec/conformance/v0.1.0/ (extracted verbatim from the
v0.1.0 tag). This proves the extracted, relicensed verifier stayed
byte-compatible with what v0.1.0 actually signed — the relicensing changed no
verification behaviour. The vectors are referenced from the checkout, not
bundled into the wheel.
"""
import json
from pathlib import Path

import pytest

from apl_verifier import VerifyError, verify_receipt

# packages/apl-verifier/tests -> repo root is parents[3]
_FROZEN = Path(__file__).resolve().parents[3] / "spec" / "conformance" / "v0.1.0"


@pytest.mark.skipif(not _FROZEN.is_dir(),
                    reason="v0.1.0 conformance vectors only present in a checkout")
def test_v010_real_receipt_verifies():
    pub = str(_FROZEN / "apl-oss-demo-key.pem")
    receipt = json.loads((_FROZEN / "receipt.json").read_text(encoding="utf-8"))
    verify_receipt(receipt, pub)  # must not raise


@pytest.mark.skipif(not _FROZEN.is_dir(),
                    reason="v0.1.0 conformance vectors only present in a checkout")
def test_v010_tampered_receipt_rejected():
    pub = str(_FROZEN / "apl-oss-demo-key.pem")
    tampered = json.loads((_FROZEN / "tampered_receipt.json").read_text(encoding="utf-8"))
    with pytest.raises(VerifyError):
        verify_receipt(tampered, pub)
