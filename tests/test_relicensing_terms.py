# SPDX-License-Identifier: FSL-1.1-ALv2
"""Rule-2 relicensing vocabulary gate.

The relicensing must not introduce the forbidden terms (patent, patent-pending,
PPA, NPA, trademark symbols) anywhere except genuine license text and the CLA's
legal clauses. Two pre-existing `patent` mentions in the docs (present at
v0.1.0) are explicitly allow-listed — they were not added by the relicensing.
Terms are matched on word boundaries so substrings like PYTHONPATH do not count.
No --deselect: always on.
"""
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# Word-boundary term match (™ and (TM) handled separately — not \w tokens).
_TERM = re.compile(r"\bpatent(?:-pending)?\b|\bPPA\b|\bNPA\b", re.IGNORECASE)
_SYMBOLS = ("™", "(TM)")  # ™, (TM)

TEXT_SUFFIXES = {".py", ".md", ".json", ".yaml", ".yml", ".txt", ".html",
                 ".css", ".js", ".toml", ".cfg", ".ini"}

# Exceptions (work-order rule 2): license text, the CLA legal clauses, and the
# report's own filename references. Plus two pre-existing doc mentions.
ALLOWED_PATH_PREFIXES = ("LICENSES/", "packages/apl-verifier/LICENSE")
ALLOWED_EXACT = {"CLA.md", "RELICENSE_REPORT.md",
                 # this gate's own source names the forbidden terms to detect them
                 "tests/test_relicensing_terms.py"}
ALLOWED_PREEXISTING = {
    ("docs/enterprise_gateway.md", "patent"),   # v0.1.0 prose, not added here
    ("docs/scenario-packs.md", "patent"),       # v0.1.0 prose, not added here
}


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
            term = m.group(0).lower()
            if (rel, term) in ALLOWED_PREEXISTING:
                continue
            offenders.append(f"{rel}: {m.group(0)!r}")
        for sym in _SYMBOLS:
            if sym in text:
                offenders.append(f"{rel}: {sym!r}")
    assert not offenders, "forbidden relicensing terms:\n" + "\n".join(offenders)
