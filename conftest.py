"""Test bootstrap: make the independent apl-verifier package importable.

From a source checkout the package under packages/apl-verifier/ is not
pip-installed, so its src/ directory is added to sys.path here. An installed
wheel finds `apl_verifier` normally and this is a harmless no-op. This mirrors
what the runtime does at import time via cli.commands._verifier_boot.
"""
import sys
from pathlib import Path

_PKG_SRC = Path(__file__).resolve().parent / "packages" / "apl-verifier" / "src"
if _PKG_SRC.is_dir() and str(_PKG_SRC) not in sys.path:
    sys.path.insert(0, str(_PKG_SRC))
