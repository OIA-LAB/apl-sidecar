# SPDX-License-Identifier: FSL-1.1-ALv2
"""Bootstrap + key-resolution bridge to the independent apl-verifier package.

The verification LAYER lives in the separately licensed `apl_verifier` package
(Apache-2.0). The runtime depends on it one-way. This module:

  1. makes `apl_verifier` importable from a source checkout by adding
     packages/apl-verifier/src to the front of sys.path, so a checkout always
     runs against its own in-repo verifier (matching the root conftest.py)
     even when an older apl-verifier wheel is installed; from an installed
     wheel the directory does not exist and this is a no-op;
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

# Repo root from the src layout: src/apl_sidecar/cli/commands/ -> 4 levels up.
# (The pre-src-layout depth of 2 pointed at src/apl_sidecar, so the shim never
# fired and a checkout silently fell back to any installed wheel.)
_REPO = Path(__file__).resolve().parents[4]
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


def load_receipt_json(text: str) -> dict:
    """Parse one receipt, routing through the verifier's strict parser.

    Enforces the same duplicate-key fail-close rule the verify entry points
    use, so chain-load ingestion cannot silently accept a receipt whose
    duplicated member changes value between parsers. Raises ValueError
    (json.JSONDecodeError is a ValueError) on malformed or duplicate-key input.
    """
    return apl_verifier.load_receipt_json(text)


def verify_receipt(receipt: dict, pubkey_path: str | None = None) -> None:
    """Verify a receipt, resolving the pubkey runtime-side when not supplied."""
    path = pubkey_path or resolve_pubkey_path(receipt.get("signing_key_id", ""))
    apl_verifier.verify_receipt(receipt, path)


def verify_chain(receipts: list[dict], pubkey_path: str | None = None) -> None:
    path = pubkey_path
    if path is None and receipts:
        path = resolve_pubkey_path(receipts[0].get("signing_key_id", ""))
    apl_verifier.verify_chain(receipts, path)
