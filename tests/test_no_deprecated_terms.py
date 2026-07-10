"""Canonical-vocabulary and secret-hygiene gates for the whole repo."""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

TEXT_SUFFIXES = {".py", ".md", ".json", ".yaml", ".yml", ".txt", ".html",
                 ".css", ".js", ".pem", ".gitignore", ".gitattributes"}

# built by concatenation so this scanner never matches itself
DEPRECATED_TERM = "no_single_" + "cloud"

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{30,}"),
    re.compile(r"sk-proj-[A-Za-z0-9_-]{20,}"),
    re.compile(r"AIza[0-9A-Za-z_-]{30,}"),
    re.compile(r"-----BEGIN (?:EC |RSA )?PRIVATE KEY-----"),
    re.compile(r"AKIA[0-9A-Z]{16}"),                     # AWS access key id
    re.compile(r"(?:xoxb|xoxp)-[0-9A-Za-z-]{20,}"),      # slack-style tokens
]


def _iter_files():
    for f in REPO.rglob("*"):
        if not f.is_file():
            continue
        parts = set(f.parts)
        if {".git", "__pycache__", ".pytest_cache", "keys", "out"} & parts:
            continue
        if f.suffix.lower() in TEXT_SUFFIXES or f.name in (".gitignore",
                                                           ".gitattributes"):
            yield f


def test_no_deprecated_vocabulary():
    hits = [str(f) for f in _iter_files()
            if DEPRECATED_TERM in f.read_text(encoding="utf-8", errors="replace")]
    assert not hits, f"deprecated term found in: {hits}"


def test_canonical_term_present_where_expected():
    receipt = (REPO / "examples" / "00_private_idea" / "receipt.json").read_text(
        encoding="utf-8")
    assert "no_single_provider_saw_full" in receipt


def test_no_secret_patterns_anywhere():
    hits = []
    for f in _iter_files():
        text = f.read_text(encoding="utf-8", errors="replace")
        for pat in SECRET_PATTERNS:
            if pat.search(text):
                hits.append(f"{f}: {pat.pattern}")
    assert not hits, "possible secrets:\n" + "\n".join(hits)


def test_no_private_keys_committed():
    # the ONLY .pem files allowed are PUBLIC keys under spec/
    for f in REPO.rglob("*.pem"):
        if {".git", "keys"} & set(f.parts):
            continue
        assert f.parent == REPO / "spec", f"unexpected pem location: {f}"
        text = f.read_text(encoding="utf-8", errors="replace")
        assert "PRIVATE" not in text, f"private key material in {f}"


def test_playground_has_no_external_origins():
    app = REPO / "app" / "local_playground"
    for f in app.glob("*"):
        if f.suffix.lower() not in (".html", ".js", ".css"):
            continue
        text = f.read_text(encoding="utf-8")
        assert "https://" not in text, f.name
        assert "http://" not in text.replace("http://127.0.0.1", ""), f.name
        assert "cdn" not in text.lower(), f.name
