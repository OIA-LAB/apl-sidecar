# SPDX-License-Identifier: FSL-1.1-ALv2
"""Every tamper vector must FAIL verification; the leak-check must pass.

Verification goes through the runtime bridge (auto-resolves the spec demo key);
the CLI failure path is exercised via `apl verify`.
"""
import json
from pathlib import Path

import pytest

from apl_verifier import FAIL_MESSAGE, VerifyError
from cli.apl import main as apl_main
from cli.commands import _verifier_boot
from cli.commands import mask

REPO = Path(__file__).resolve().parents[1]

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
    with pytest.raises(VerifyError):
        _verifier_boot.verify_receipt(_load(TV / name))


def test_all_four_vectors_exist():
    assert len(list(TV.glob("*.json"))) == 4


@pytest.mark.parametrize("ex", ["00_private_matter", "01_private_code_context"])
def test_example_tampered_receipt_fails(ex):
    with pytest.raises(VerifyError):
        _verifier_boot.verify_receipt(
            _load(REPO / "examples" / ex / "tampered_receipt.example.json"))


def test_cli_reports_failure_message(capsys):
    code = apl_main(["verify", str(TV / "tamper_payload_changed.json")])
    assert code == 1
    assert FAIL_MESSAGE in capsys.readouterr().out


@pytest.mark.parametrize("ex", ["00_private_matter", "01_private_code_context"])
def test_mask_leak_check_passes(ex):
    assert mask.run(str(REPO / "examples" / ex)) == 0


def test_single_byte_flip_fails():
    r = _load(REPO / "examples" / "00_private_matter" / "receipt.json")
    r["provenance"]["example_id"] = r["provenance"]["example_id"] + "x"
    with pytest.raises(VerifyError):
        _verifier_boot.verify_receipt(r)
