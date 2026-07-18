# SPDX-License-Identifier: Apache-2.0
"""`apl-verify` console entry point — offline receipt verification.

Usage:
    apl-verify <receipt.json> [more_receipts_in_chain_order...] --pubkey key.pem

`--pubkey` is REQUIRED: this tool never searches repo-relative key directories.
Exit codes: 0 = verified, 1 = failed, 2 = usage.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from .receipt import FAIL_MESSAGE, VALID_MESSAGE, VerifyError, verify_chain

_USAGE = "usage: apl-verify <receipt.json>... --pubkey key.pem"


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    pubkey = None
    if "--pubkey" in argv:
        i = argv.index("--pubkey")
        try:
            pubkey = argv[i + 1]
        except IndexError:
            print(_USAGE)
            return 2
        del argv[i:i + 2]
    if not argv or not pubkey:
        print(_USAGE)
        return 2
    receipts = []
    for path in argv:
        try:
            receipts.append(json.loads(Path(path).read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            print(f"{FAIL_MESSAGE} ({path}: {exc})")
            return 1
    try:
        verify_chain(receipts, pubkey)
    except VerifyError as exc:
        print(f"{FAIL_MESSAGE} ({exc})")
        return 1
    print(VALID_MESSAGE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
