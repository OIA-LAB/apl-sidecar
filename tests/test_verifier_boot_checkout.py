# SPDX-License-Identifier: FSL-1.1-ALv2
"""A source checkout must run against its own in-repo apl-verifier.

The runtime bridge (cli.commands._verifier_boot) adds packages/apl-verifier/src
to sys.path so a checkout uses the verifier that ships with it. Before the
src-layout depth fix, the shim computed the wrong repo root and never fired, so
a checkout with an older apl-verifier wheel installed silently used the wheel:
`apl inspect` then accepted receipts the in-repo verifier rejects (for example
numeric literals that overflow to infinity, such as 1e400).

These tests run in a subprocess so the root conftest.py sys.path insertion
cannot mask a broken shim (it did exactly that for the rest of the suite).
"""
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PKG_SRC = REPO / "packages" / "apl-verifier" / "src"


def _run(code: str) -> subprocess.CompletedProcess:
    # Make apl_sidecar importable even in an uninstalled checkout; the
    # apl-verifier package path is deliberately NOT added here -- reaching it
    # is the bridge shim's job, which is what these tests check.
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO / "src") + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "-c", code], cwd=str(REPO), env=env,
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def test_checkout_shim_resolves_in_repo_verifier():
    """Importing the bridge from a checkout must resolve apl_verifier to
    packages/apl-verifier/src, not to an installed wheel (or fail to import)."""
    proc = _run(
        "from apl_sidecar.cli.commands import _verifier_boot\n"
        "import apl_verifier, pathlib\n"
        "print(pathlib.Path(apl_verifier.__file__).resolve())\n")
    assert proc.returncode == 0, proc.stdout
    resolved = Path(proc.stdout.strip().splitlines()[-1])
    assert PKG_SRC.resolve() in resolved.parents, (
        f"apl_verifier resolved outside the checkout: {resolved}")


def test_inspect_ingestion_rejects_overflow_via_bridge():
    """The parse-only ingestion path (apl inspect / chain-load) must reject an
    overflow-to-infinity numeric literal through the bridge, proving the
    checkout picks up the in-repo finite-number guard."""
    proc = _run(
        "from apl_sidecar.cli.commands import _verifier_boot\n"
        "try:\n"
        "    _verifier_boot.load_receipt_json('{\"exposure_ratio\": 1e400}')\n"
        "except ValueError as e:\n"
        "    assert 'non-finite' in str(e), e\n"
        "    print('REJECTED-NON-FINITE')\n"
        "else:\n"
        "    raise SystemExit('overflow literal was accepted')\n")
    assert proc.returncode == 0, proc.stdout
    assert "REJECTED-NON-FINITE" in proc.stdout
