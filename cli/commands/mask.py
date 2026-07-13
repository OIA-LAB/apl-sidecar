"""apl mask -- show the masking plan and LEAK-CHECK the provider payloads.

P0 masking is user-guided: the plan declares which fields are local-only.
This command's real value is the check: no local-only VALUE may appear in
any provider payload. If one does, masking failed -- exit 1.
"""
from __future__ import annotations

from . import _common as c


def run(example_dir: str) -> int:
    paths = c.example_paths(example_dir)
    plan = c.load_masking_plan(paths)

    print("=" * 64)
    print(f"APL MASK -- {paths['dir'].name} (guided_curated_p0)")
    print("=" * 64)
    print(f"task_type: {plan['task_type']}")
    print("\nlocal-only fields (declared in masking_plan.yaml):")
    for f in plan.get("local_only_fields", []):
        print(f"  - {f}")
    print("\npreserved task signals:")
    for s in plan.get("preserved_task_signals", []):
        print(f"  - {s}")

    print("\n-- LEAK CHECK " + "-" * 48)
    leaks = c.leak_findings(paths)
    if leaks:
        print("LEAK CHECK FAILED:")
        for leak in leaks:
            print(f"  ! {leak}")
        return 1
    print("OK -- no local-only value appears in any provider payload.")
    print("note: P0 check is exact-substring only -- paraphrased or partial")
    print("      leakage is NOT detected. See docs/masking_levels.md (L1/L2).")
    return 0
