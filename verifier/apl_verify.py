"""DEPRECATED shim — the verifier moved to the independent `apl_verifier`
package (Apache-2.0) under packages/apl-verifier/.

Kept only for backward compatibility with `sys.path.insert(REPO/"verifier")
+ import apl_verify` call sites. It re-exports the package API and preserves
the old key-resolution behaviour (resolve a signing_key_id against the user
key dir and the packaged spec/ demo key when no --pubkey is given) so existing
callers keep working unchanged.

Scheduled for removal in v0.3. New code must import from `apl_verifier`
directly (pure verifier; pass an explicit --pubkey) or, for runtime callers
that want the old auto key resolution, from cli.commands._verifier_boot.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

warnings.warn(
    "verifier.apl_verify is deprecated; import from the apl_verifier package "
    "(Apache-2.0) or cli.commands._verifier_boot. Removal in v0.3.",
    DeprecationWarning,
    stacklevel=2,
)

# Make the independent package importable from a source checkout, then bridge
# to it for the runtime-side key resolution the old API implied.
_REPO = Path(__file__).resolve().parents[1]
_PKG_SRC = _REPO / "packages" / "apl-verifier" / "src"
if _PKG_SRC.is_dir() and str(_PKG_SRC) not in sys.path:
    sys.path.insert(0, str(_PKG_SRC))

from apl_verifier import (  # noqa: E402,F401  (re-export)
    FAIL_MESSAGE,
    REQUIRED_FIELDS,
    VALID_MESSAGE,
    VerifyError,
    canonical_bytes,
    compute_receipt_hash,
    load_public_key,
)
from apl_verifier.trust import normalize_host as _normalize_host  # noqa: E402,F401
from apl_verifier.trust import trust_domain as _trust_domain  # noqa: E402,F401
from apl_verifier.receipt import (  # noqa: E402,F401
    _check_max_single_seat,
    _check_shape,
    _check_trust_domain_consistency,
    _reject_duplicates,
)


def _bridge():
    """The runtime-side verify bridge (does key resolution). Imported lazily to
    avoid a hard dependency on the cli package when only the pure helpers are
    used."""
    from cli.commands import _verifier_boot
    return _verifier_boot


def verify_receipt(receipt: dict, pubkey_path: str | None = None) -> None:
    """Backward-compatible: resolves the pubkey from user/spec dirs when not
    given, exactly as the old standalone verifier did."""
    _bridge().verify_receipt(receipt, pubkey_path)


def verify_chain(receipts: list[dict], pubkey_path: str | None = None) -> None:
    _bridge().verify_chain(receipts, pubkey_path)


def main(argv=None) -> int:
    """Old CLI entry: verify a receipt chain, auto-resolving the pubkey when no
    --pubkey is passed (unlike the new pure `apl-verify` console script, which
    requires --pubkey)."""
    import json
    argv = list(sys.argv[1:] if argv is None else argv)
    pubkey = None
    if "--pubkey" in argv:
        i = argv.index("--pubkey")
        try:
            pubkey = argv[i + 1]
        except IndexError:
            print("usage: apl_verify.py <receipt.json>... [--pubkey key.pem]")
            return 2
        del argv[i:i + 2]
    if not argv:
        print("usage: apl_verify.py <receipt.json>... [--pubkey key.pem]")
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
