"""Schemas must accept the shipped artifacts (receipts + policy manifest)."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tests"))

from _schema_check import check  # noqa: E402


def _load(p):
    return json.loads(p.read_text(encoding="utf-8"))


RECEIPT_SCHEMA = _load(REPO / "spec" / "receipt.schema.json")
POLICY_SCHEMA = _load(REPO / "spec" / "policy_manifest.schema.json")


def test_policy_manifest_matches_schema():
    errors = check(_load(REPO / "spec" / "demo_policy_manifest.json"), POLICY_SCHEMA)
    assert not errors, errors


def test_example_receipts_match_schema():
    for ex in ("00_private_idea", "01_private_code_context"):
        r = _load(REPO / "examples" / ex / "receipt.json")
        errors = check(r, RECEIPT_SCHEMA)
        assert not errors, (ex, errors)


def test_chain_receipts_match_schema():
    vc = REPO / "spec" / "conformance_vectors" / "valid_chain"
    for p in sorted(vc.glob("*.json")):
        errors = check(_load(p), RECEIPT_SCHEMA)
        assert not errors, (p.name, errors)


def test_schema_rejects_bad_receipt():
    r = _load(REPO / "examples" / "00_private_idea" / "receipt.json")
    r.pop("no_single_provider_saw_full")
    assert check(r, RECEIPT_SCHEMA)  # must produce errors
    r2 = _load(REPO / "examples" / "00_private_idea" / "receipt.json")
    r2["max_single_provider_exposure"] = 1.5
    assert check(r2, RECEIPT_SCHEMA)


def test_policy_caps_respected_by_examples():
    policy = _load(REPO / "spec" / "demo_policy_manifest.json")
    for ex in ("00_private_idea", "01_private_code_context"):
        r = _load(REPO / "examples" / ex / "receipt.json")
        assert r["max_single_provider_exposure"] <= \
            policy["max_single_provider_exposure"], ex
        assert r["policy_id"] == policy["policy_id"]
