# SPDX-License-Identifier: FSL-1.1-ALv2
"""Every tracked .py must carry the SPDX header for its licensing layer.

Runtime code is FSL-1.1-ALv2; the independent verifier package under
packages/apl-verifier/ is Apache-2.0. The header must be within the first
three lines (after an optional shebang / coding cookie) and must name the
layer's exact license. No --deselect: this gate is always on.
"""
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

RUNTIME_SPDX = "# SPDX-License-Identifier: FSL-1.1-ALv2"
VERIFIER_SPDX = "# SPDX-License-Identifier: Apache-2.0"
VERIFIER_PREFIX = "packages/apl-verifier/"


def _tracked_py():
    out = subprocess.run(["git", "ls-files", "*.py"], cwd=REPO,
                         capture_output=True, text=True, check=True).stdout
    return [line.strip() for line in out.splitlines() if line.strip()]


def _expected(rel: str) -> str:
    return VERIFIER_SPDX if rel.startswith(VERIFIER_PREFIX) else RUNTIME_SPDX


def test_every_py_has_correct_spdx_header():
    wrong = {}
    for rel in _tracked_py():
        head = (REPO / rel).read_text(encoding="utf-8").splitlines()[:3]
        expected = _expected(rel)
        spdx_lines = [ln for ln in head if "SPDX-License-Identifier" in ln]
        if not spdx_lines:
            wrong[rel] = "missing SPDX header"
        elif spdx_lines[0].strip() != expected:
            wrong[rel] = f"got {spdx_lines[0].strip()!r}, expected {expected!r}"
    assert not wrong, "SPDX header problems:\n" + "\n".join(
        f"  {k}: {v}" for k, v in sorted(wrong.items()))
