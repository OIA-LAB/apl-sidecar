"""apl verify -- offline receipt verification (schema, hash, signature, chain).

Delegates to the independent apl-verifier package via the runtime bridge, which
resolves the signing key from the user key dir / packaged spec key when no
--pubkey is supplied.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import _verifier_boot
from ._verifier_boot import apl_verifier as _verifier


def run(receipt_paths: list[str], pubkey: str | None = None) -> int:
    receipts = []
    for path in receipt_paths:
        try:
            receipts.append(json.loads(Path(path).read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            print(f"{_verifier.FAIL_MESSAGE} ({path}: {exc})")
            return 1
    if not receipts:
        print("usage: apl verify <receipt.json>... [--pubkey key.pem]")
        return 2
    try:
        _verifier_boot.verify_chain(receipts, pubkey)
    except _verifier.VerifyError as exc:
        print(f"{_verifier.FAIL_MESSAGE} ({exc})")
        return 1
    print(_verifier.VALID_MESSAGE)
    return 0
