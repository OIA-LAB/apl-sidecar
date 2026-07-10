"""apl inspect -- show exposure accounting and provenance from a receipt."""
from __future__ import annotations

import json
from pathlib import Path

from . import _common as c


def run(receipt_path: str) -> int:
    p = Path(receipt_path)
    if not p.exists():
        print(f"receipt not found: {p}")
        return 1
    r = json.loads(p.read_text(encoding="utf-8"))
    policy = c.load_policy_manifest()

    print("=" * 64)
    print(f"APL INSPECT -- {p}")
    print("=" * 64)
    print(f"run_id:        {r['run_id']}")
    print(f"task_type:     {r['task_type']}")
    print(f"policy_id:     {r['policy_id']}")
    print(f"masking_level: {r['masking_level']}")

    print("\n-- PROVIDER EXPOSURE " + "-" * 41)
    for e in r["single_provider_exposure"]:
        print(f"  {e['provider_id']}: {e['exposure_ratio']:.1%}")
    print(f"  max_single_provider_exposure: "
          f"{r['max_single_provider_exposure']:.1%}")
    print(f"  max allowed by policy:        "
          f"{policy['max_single_provider_exposure']:.1%}")
    print(f"  no_single_provider_saw_full:  {r['no_single_provider_saw_full']}")

    print("\n-- LOCAL-ONLY " + "-" * 48)
    print(f"  {len(r['local_only_hashes'])} fields stayed local "
          f"(only fingerprints entered the receipt):")
    for h in r["local_only_hashes"]:
        print(f"    {h['field']}: sha256:{h['sha256'][:16]}...")

    print("\n-- PROVENANCE " + "-" * 48)
    for k, v in sorted(r["provenance"].items()):
        print(f"  {k}: {v}")
    print(f"\n  prev_receipt_hash: {r['prev_receipt_hash']}")
    print(f"  receipt_hash:      {r['receipt_hash']}")
    print(f"  signing_key_id:    {r['signing_key_id']}")
    return 0
