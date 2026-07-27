# SPDX-License-Identifier: FSL-1.1-ALv2
"""apl rehydrate -- combine mock provider answers with local-only context.

Rehydration happens HERE, on your machine. Providers only ever saw the
abstract payloads; the sensitive specifics are reintroduced locally.
"""
from __future__ import annotations

from . import _common as c


def run(example_dir: str) -> int:
    paths = c.example_paths(example_dir)
    local_only = c.load_local_only(paths)

    print("=" * 64)
    print(f"APL REHYDRATE -- {paths['dir'].name} (local machine only)")
    print("=" * 64)
    for provider, answer_path in paths["answers"].items():
        print(f"\n-- {provider} answered (saw only its payload) " + "-" * 8)
        text = c.read_text(answer_path).strip()
        print(text[:400] + ("..." if len(text) > 400 else ""))

    print("\n-- LOCAL CONTEXT REINTRODUCED " + "-" * 32)
    for field in sorted(local_only):
        print(f"  + {field} (stayed local, hash in receipt)")

    print("\n-- FINAL REHYDRATED ANSWER " + "-" * 35)
    print(c.read_text(paths["rehydrated"]).strip())
    print("\nNo single provider saw the full task context.")
    return 0
