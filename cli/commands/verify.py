"""apl verify -- offline receipt verification (schema, hash, signature, chain)."""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "verifier"))

import apl_verify  # noqa: E402


def run(receipt_paths: list[str], pubkey: str | None = None) -> int:
    argv = list(receipt_paths)
    if pubkey:
        argv += ["--pubkey", pubkey]
    return apl_verify.main(argv)
