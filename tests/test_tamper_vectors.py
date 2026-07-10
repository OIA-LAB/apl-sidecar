"""Every tamper vector must FAIL verification; the leak-check must pass."""
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "verifier"))
sys.path.insert(0, str(REPO / "cli"))

import apl_verify  # noqa: E402

TV = REPO / "spec" / "conformance_vectors" / "tamper_vectors"


def _load(p):
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", [
    "tamper_payload_changed.json",
    "tamper_provider_changed.json",
    "tamper_prev_hash_changed.json",
    "tamper_signature_removed.json",
])
def test_tamper_vector_fails(name):
    with pytest.raises(apl_verify.VerifyError):
        apl_verify.verify_receipt(_load(TV / name))


def test_all_four_vectors_exist():
    assert len(list(TV.glob("*.json"))) == 4


@pytest.mark.parametrize("ex", ["00_private_idea", "01_private_code_context"])
def test_example_tampered_receipt_fails(ex):
    with pytest.raises(apl_verify.VerifyError):
        apl_verify.verify_receipt(
            _load(REPO / "examples" / ex / "tampered_receipt.example.json"))


def test_cli_reports_failure_message(capsys):
    code = apl_verify.main([str(TV / "tamper_payload_changed.json")])
    assert code == 1
    assert apl_verify.FAIL_MESSAGE in capsys.readouterr().out


@pytest.mark.parametrize("ex", ["00_private_idea", "01_private_code_context"])
def test_mask_leak_check_passes(ex):
    from commands import mask
    assert mask.run(str(REPO / "examples" / ex)) == 0


def test_single_byte_flip_fails():
    r = _load(REPO / "examples" / "00_private_idea" / "receipt.json")
    r["provenance"]["example_id"] = r["provenance"]["example_id"] + "x"
    with pytest.raises(apl_verify.VerifyError):
        apl_verify.verify_receipt(r)
