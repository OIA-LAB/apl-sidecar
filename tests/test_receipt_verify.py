# SPDX-License-Identifier: FSL-1.1-ALv2
"""Valid receipts and chains must verify; the CLI must agree.

Verification lives in the independent apl-verifier package. Receipts here are
signed by the packaged spec demo key, so these tests go through the runtime
bridge (cli.commands._verifier_boot), which resolves that key. The bridge in
turn calls the pure apl_verifier package.
"""
import json
from pathlib import Path

from apl_verifier import VALID_MESSAGE, VerifyError
from cli.apl import main as apl_main
from cli.commands import _verifier_boot

REPO = Path(__file__).resolve().parents[1]

EXAMPLES = [REPO / "examples" / "00_private_idea",
            REPO / "examples" / "01_private_code_context"]
CHAIN = [REPO / "spec" / "conformance_vectors" / "valid_chain" / "receipt_001.json",
         REPO / "spec" / "conformance_vectors" / "valid_chain" / "receipt_002.json"]


def _load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def test_example_receipts_verify():
    for ex in EXAMPLES:
        _verifier_boot.verify_receipt(_load(ex / "receipt.json"))  # must not raise


def test_valid_chain_verifies():
    _verifier_boot.verify_chain([_load(p) for p in CHAIN])  # must not raise


def test_chain_order_matters():
    import pytest
    with pytest.raises(VerifyError):
        _verifier_boot.verify_chain([_load(CHAIN[1]), _load(CHAIN[0])])


def test_cli_verify_exit_codes(capsys):
    assert apl_main(["verify", str(EXAMPLES[0] / "receipt.json")]) == 0
    assert VALID_MESSAGE in capsys.readouterr().out
    assert apl_main(["verify", *[str(p) for p in CHAIN]]) == 0
    assert apl_main(["verify"]) == 2


def test_exposure_recomputable_from_payload_files():
    """The receipt's exposure numbers must match the shipped payload files."""
    for ex in EXAMPLES:
        receipt = _load(ex / "receipt.json")
        original = (ex / "input.original.example.txt").read_text(
            encoding="utf-8").replace("\r\n", "\n")
        payloads = {"mock_provider_a": "provider_a_payload.txt",
                    "mock_provider_b": "provider_b_payload.txt"}
        for e in receipt["single_provider_exposure"]:
            payload = (ex / payloads[e["provider_id"]]).read_text(
                encoding="utf-8").replace("\r\n", "\n")
            assert abs(e["exposure_ratio"] - len(payload) / len(original)) < 1e-6
        assert receipt["no_single_provider_saw_full"] is True
