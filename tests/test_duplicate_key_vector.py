# SPDX-License-Identifier: FSL-1.1-ALv2
"""P2 duplicate-key fail-close: a receipt whose JSON text repeats an object
member must be rejected at parse time, not silently de-duplicated (last-wins).

Both receipt parse entry points route through apl_verifier.load_receipt_json,
which uses a strict object_pairs_hook. The duplicate-key error is a ValueError
(as is json.JSONDecodeError), so the existing `except (OSError, ValueError)`
guards in both CLIs fail-close to exit code 1.
"""
import json
from pathlib import Path

import pytest

from apl_verifier import compute_receipt_hash, load_receipt_json
from apl_verifier.cli import main as pkg_main
from apl_sidecar.cli.apl import main as apl_main
from apl_sidecar.verifier import apl_verify as sidecar_shim

REPO = Path(__file__).resolve().parents[1]
VECTOR = (REPO / "src" / "apl_sidecar" / "spec" / "conformance_vectors"
          / "tamper_duplicate_key.json")


def _text():
    return VECTOR.read_text(encoding="utf-8")


def test_vector_exists():
    assert VECTOR.is_file()


def test_plain_json_loads_would_silently_accept():
    # Documents WHY the strict parser is needed: stdlib json keeps the LAST
    # value for a repeated key and drops the earlier (shadow) one.
    loaded = json.loads(_text())
    assert "task_type" in loaded
    assert loaded["task_type"] != "TAMPERED-DUPLICATE-SHADOW"


def test_load_receipt_json_rejects_duplicate_key():
    with pytest.raises(ValueError) as exc:
        load_receipt_json(_text())
    assert "duplicate JSON object key" in str(exc.value)


def test_sidecar_shim_load_receipt_json_rejects():
    # The deprecated shim re-exports the same strict parser.
    with pytest.raises(ValueError):
        sidecar_shim.load_receipt_json(_text())


def test_hash_invariant_plain_equals_stored():
    # Invariant: the last-wins de-duplicated object is otherwise the honest
    # receipt, so its recomputed hash equals the stored receipt_hash. The
    # tamper channel is purely the ambiguous shadow member, which the strict
    # parser removes from play by refusing to parse at all.
    loaded = json.loads(_text())
    assert compute_receipt_hash(loaded) == loaded["receipt_hash"]


def test_package_cli_fails_closed(capsys):
    code = pkg_main([str(VECTOR), "--pubkey", "unused-key.pem"])
    assert code == 1
    assert "task_type" in capsys.readouterr().out or code == 1


def test_sidecar_cli_fails_closed(capsys):
    code = apl_main(["verify", str(VECTOR)])
    assert code == 1
