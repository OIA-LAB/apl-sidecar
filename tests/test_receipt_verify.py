"""Valid receipts and chains must verify; the CLI must agree."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "verifier"))
sys.path.insert(0, str(REPO / "cli"))

import apl_verify  # noqa: E402

EXAMPLES = [REPO / "examples" / "00_private_idea",
            REPO / "examples" / "01_private_code_context"]
CHAIN = [REPO / "spec" / "conformance_vectors" / "valid_chain" / "receipt_001.json",
         REPO / "spec" / "conformance_vectors" / "valid_chain" / "receipt_002.json"]


def _load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def test_example_receipts_verify():
    for ex in EXAMPLES:
        apl_verify.verify_receipt(_load(ex / "receipt.json"))  # must not raise


def test_valid_chain_verifies():
    apl_verify.verify_chain([_load(p) for p in CHAIN])  # must not raise


def test_chain_order_matters():
    import pytest
    with pytest.raises(apl_verify.VerifyError):
        apl_verify.verify_chain([_load(CHAIN[1]), _load(CHAIN[0])])


def test_cli_verify_exit_codes(capsys):
    assert apl_verify.main([str(EXAMPLES[0] / "receipt.json")]) == 0
    assert apl_verify.VALID_MESSAGE in capsys.readouterr().out
    assert apl_verify.main([str(p) for p in CHAIN]) == 0
    assert apl_verify.main([]) == 2


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
