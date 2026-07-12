"""Shared helpers for APL Sidecar CLI commands. Offline by design."""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

PROVIDERS = ("mock_provider_a", "mock_provider_b")
PAYLOAD_FILES = {"mock_provider_a": "provider_a_payload.txt",
                 "mock_provider_b": "provider_b_payload.txt"}
ANSWER_FILES = {"mock_provider_a": "mock_answer_a.txt",
                "mock_provider_b": "mock_answer_b.txt"}

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def new_ulid() -> str:
    ts = int(time.time() * 1000) & ((1 << 48) - 1)
    rand = int.from_bytes(os.urandom(10), "big")
    val = (ts << 80) | rand
    return "".join(_CROCKFORD[(val >> (5 * i)) & 31] for i in range(25, -1, -1))


def normalize(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def text_sha256(text: str) -> str:
    return hashlib.sha256(normalize(text).encode("utf-8")).hexdigest()


def read_text(path: Path) -> str:
    return normalize(path.read_text(encoding="utf-8"))

def estimated_tokens(text: str) -> int:
    """Presentation-only estimate; receipt exposure remains character based."""
    normalized = normalize(text).strip()
    return (len(normalized) + 3) // 4 if normalized else 0


def example_paths(example_dir: str | Path) -> dict:
    requested = Path(example_dir)
    if not requested.exists():
        raise SystemExit(f"example path not found: {requested}")
    d = requested.parent if requested.is_file() else requested
    original = requested if requested.is_file() else d / "input.original.example.txt"
    return {
        "dir": d,
        "original": original,
        "masking_plan": d / "masking_plan.yaml",
        "local_only": d / "local_only.json",
        "payloads": {p: d / PAYLOAD_FILES[p] for p in PROVIDERS},
        "answers": {p: d / ANSWER_FILES[p] for p in PROVIDERS},
        "rehydrated": d / "final_rehydrated_answer.txt",
        "receipt": d / "receipt.json",
        "receipt_local": d / "receipt.local.json",
    }


def load_local_only(paths: dict) -> dict:
    return json.loads(paths["local_only"].read_text(encoding="utf-8"))


def load_masking_plan(paths: dict) -> dict:
    import yaml
    return yaml.safe_load(paths["masking_plan"].read_text(encoding="utf-8"))


def exposure_view(paths: dict) -> dict:
    """Character-count exposure accounting (RECEIPT_STANDARD section 1)."""
    original = read_text(paths["original"])
    n = len(original)
    per = {}
    saw_full = False
    for provider, payload_path in paths["payloads"].items():
        payload = read_text(payload_path)
        ratio = round(len(payload) / n, 6) if n else 0.0
        per[provider] = {"chars": len(payload), "exposure_ratio": ratio,
                         "payload_sha256": text_sha256(payload)}
        if payload == original:
            saw_full = True
    return {"original_chars": n, "providers": per,
            "max_single_provider_exposure": round(
                max((v["exposure_ratio"] for v in per.values()), default=0.0), 6),
            "no_single_provider_saw_full": not saw_full}


def leak_findings(paths: dict) -> list[str]:
    """Exact-substring leak check shared by `apl mask` and `apl run-live`.

    One rule, one implementation: the preview gate and the transmission gate
    must never disagree. P0 limitation: exact substrings >= 4 chars only —
    paraphrased or partial leakage is NOT detected (docs/masking_levels.md).
    """
    local_only = load_local_only(paths)
    payload_texts = {p: read_text(path).lower()
                     for p, path in paths["payloads"].items()}
    findings = []
    for fld, value in local_only.items():
        needle = (value if isinstance(value, str) else str(value)).lower().strip()
        if len(needle) < 4:
            continue  # too short to be a meaningful leak signal
        for provider, text in payload_texts.items():
            if needle in text:
                findings.append(f"{fld!r} value found in {provider} payload")
    return findings


def load_policy_manifest() -> dict:
    p = REPO / "spec" / "demo_policy_manifest.json"
    return json.loads(p.read_text(encoding="utf-8"))
