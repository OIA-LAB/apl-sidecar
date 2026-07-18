# SPDX-License-Identifier: FSL-1.1-ALv2
"""Rule-2 relicensing vocabulary gate (term-scoped).

Assertion terms -- "patent-pending", "PPA", "NPA", and the trademark symbols
-- must not appear anywhere in the tree, with no per-file exception, save two
narrow classes: (a) genuine verbatim license text, and (b) the two meta-
documents that must name the terms in order to describe or detect them (this
gate's own source and RELICENSE_REPORT.md).

The bare word "patent" is NOT an assertion term and is permitted everywhere:
it is ordinary legal explanation (e.g. LICENSING.md's FSL/Apache patent-grant
FAQ, or the CLA's patent-license grant). So LICENSING.md, CLA.md and general
docs are scanned with no exception -- an authored legal file is exactly the
door that must stay watched -- yet their bare "patent" usages pass.

Terms are matched on word boundaries so substrings like PYTHONPATH do not
count. No --deselect: always on.
"""
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Assertion terms only. The bare word "patent" is intentionally absent -- it is
# a legal-explanation word, permitted everywhere. (The trademark symbols are not
# \w tokens, so they are checked separately below.)
_TERM = re.compile(r"\bpatent-pending\b|\bPPA\b|\bNPA\b", re.IGNORECASE)
_SYMBOLS = ("™", "(TM)")

TEXT_SUFFIXES = {".py", ".md", ".json", ".yaml", ".yml", ".txt", ".html",
                 ".css", ".js", ".toml", ".cfg", ".ini"}

# Exceptions are deliberately minimal. Assertion terms are zero-tolerance in
# authored docs -- LICENSING.md, CLA.md and general docs are all scanned, on
# purpose. Only two classes are exempt:
#   (1) genuine verbatim license text (upstream, not authored here);
#   (2) the two meta-documents that must literally name the terms: this gate's
#       own source, and RELICENSE_REPORT.md (which discusses the PPA/NPA tokens).
ALLOWED_PATH_PREFIXES = ("LICENSES/", "packages/apl-verifier/LICENSE")
ALLOWED_EXACT = {"RELICENSE_REPORT.md",
                 "tests/test_relicensing_terms.py"}


def _tracked_text_files():
    out = subprocess.run(["git", "ls-files"], cwd=REPO,
                         capture_output=True, text=True, check=True).stdout
    for line in out.splitlines():
        rel = line.strip()
        if not rel:
            continue
        name = rel.rsplit("/", 1)[-1]
        if name.startswith("LICENSE") or rel.startswith(ALLOWED_PATH_PREFIXES):
            continue
        if rel in ALLOWED_EXACT:
            continue
        p = REPO / rel
        if p.suffix.lower() in TEXT_SUFFIXES:
            yield rel, p


def test_no_new_forbidden_terms():
    offenders = []
    for rel, p in _tracked_text_files():
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in _TERM.finditer(text):
            offenders.append(f"{rel}: {m.group(0)!r}")
        for sym in _SYMBOLS:
            if sym in text:
                offenders.append(f"{rel}: {sym!r}")
    assert not offenders, "forbidden assertion terms:\n" + "\n".join(offenders)
