# SPDX-License-Identifier: Apache-2.0
"""Hard isolation: the verifier package must not depend on the APL runtime.

Dependency direction is one-way (runtime -> apl-verifier). This static scan
fails if any apl_verifier source imports a runtime module (cli, adapters,
relay, app), or the legacy `verifier`/`apl_verify` shim, so the layering can
never quietly invert.
"""
import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "apl_verifier"

# Top-level module names that belong to the APL runtime, not this package.
FORBIDDEN_ROOTS = {"cli", "adapters", "relay", "app", "verifier", "apl_verify",
                   "examples", "spec"}


def _imported_roots(path: Path):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom):
            # only absolute imports can reach the runtime; level>0 is in-package
            if node.level == 0 and node.module:
                yield node.module.split(".")[0]


def test_verifier_never_imports_runtime():
    offenders = {}
    for py in SRC.rglob("*.py"):
        bad = sorted(r for r in _imported_roots(py) if r in FORBIDDEN_ROOTS)
        if bad:
            offenders[str(py.relative_to(SRC))] = bad
    assert not offenders, f"apl_verifier imports runtime modules: {offenders}"
