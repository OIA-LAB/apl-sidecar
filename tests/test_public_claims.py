"""Gate unqualified prohibited privacy claims in primary public files."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PHRASES = (
    "prevents intent reconstruction", "impossible to reconstruct", "zero leakage",
    "zero exposure", "fully anonymous", "completely private", "guaranteed privacy",
    "cryptographic secrecy", "provider sees nothing", "no trace",
)
QUALIFIERS = (
    "does not", "do not", "not claim", "not prove", "is not", "cannot", "prohibited",
    "out of scope", "never claim", "doesn't", "isn't",
)


def public_files():
    yield REPO / "README.md"
    for root in (REPO / "docs", REPO / "examples", REPO / "app"):
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".md", ".txt", ".html", ".js"}:
                yield path


def test_no_unqualified_prohibited_public_claims():
    violations = []
    for path in public_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        lowered = text.lower()
        for phrase in PHRASES:
            start = 0
            while (index := lowered.find(phrase, start)) >= 0:
                context = lowered[max(0, index - 240):index + len(phrase) + 320]
                if not any(q in context for q in QUALIFIERS):
                    line = lowered.count("\n", 0, index) + 1
                    violations.append(f"{path.relative_to(REPO)}:{line}: {phrase}")
                start = index + len(phrase)
    assert not violations, "unqualified prohibited claims:\n" + "\n".join(violations)
