# SPDX-License-Identifier: FSL-1.1-ALv2
"""Bootstrap + key-resolution bridge to the independent apl-verifier package.

The verification LAYER lives in the separately licensed `apl_verifier` package
(Apache-2.0). The runtime depends on it one-way. This module:

  1. makes `apl_verifier` importable from a source checkout (where the package
     has not been pip-installed) by adding packages/apl-verifier/src to
     sys.path as a fallback — an installed wheel finds it normally and this is
     a no-op;
  2. keeps *key-location policy* on the runtime side (the user key dir and the
     packaged spec demo key), resolving a signing_key_id to a concrete PEM path
     and passing it explicitly into the pure verifier. The verifier package
     itself never searches the filesystem.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from . import _resources

_REPO = Path(__file__).resolve().parents[2]
_PKG_SRC = _REPO / "packages" / "apl-verifier" / "src"
if _PKG_SRC.is_dir() and str(_PKG_SRC) not in sys.path:
    sys.path.insert(0, str(_PKG_SRC))

import apl_verifier  # noqa: E402  (after the sys.path shim above)

_KEY_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")


def resolve_pubkey_path(signing_key_id: str) -> str:
    """Resolve a signing_key_id to a public-key PEM path, runtime-side.

    Search order (first hit wins): the user key dir (~/.apl-sidecar/keys or
    $APL_KEY_DIR), then the packaged spec/ demo key. The id is validated
    against the same strict allowlist the verifier uses, so it can never
    contain a path separator. Raises apl_verifier.VerifyError when no key is
    found, matching the verifier's failure mode.
    """
    if not _KEY_ID.match(str(signing_key_id)):
        raise apl_verifier.VerifyError(
            "signing_key_id must match [A-Za-z0-9._-]{1,64} (no path separators)")
    candidates = [_resources.user_key_dir() / f"{signing_key_id}.pem"]
    for d in candidates:
        try:
            d.resolve().relative_to(d.parent.resolve())
        except ValueError:
            continue
        if d.exists():
            return str(d)
    # packaged spec demo key (works from a source checkout and an installed wheel)
    try:
        spec_key = _resources.spec_key_path(f"{signing_key_id}.pem")
    except FileNotFoundError:
        spec_key = None
    if spec_key is not None and Path(spec_key).exists():
        return str(spec_key)
    raise apl_verifier.VerifyError(
        f"no public key found for signing_key_id={signing_key_id!r}")


def verify_receipt(receipt: dict, pubkey_path: str | None = None) -> None:
    """Verify a receipt, resolving the pubkey runtime-side when not supplied."""
    path = pubkey_path or resolve_pubkey_path(receipt.get("signing_key_id", ""))
    apl_verifier.verify_receipt(receipt, path)


def verify_chain(receipts: list[dict], pubkey_path: str | None = None) -> None:
    path = pubkey_path
    if path is None and receipts:
        path = resolve_pubkey_path(receipts[0].get("signing_key_id", ""))
    apl_verifier.verify_chain(receipts, path)
