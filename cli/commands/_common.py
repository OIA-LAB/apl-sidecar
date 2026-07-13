"""Shared helpers for APL Sidecar CLI commands. Offline by design."""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlsplit

from . import _resources

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


# Supported fragment range for this version. Hard limit, not advisory:
# the CLI, receipt viewer and docs are validated for 2..5 only, manual
# splitting quality degrades beyond that, and every extra seat widens the
# set of parties that see something (see docs/fragmentation.md).
FRAGMENT_MIN, FRAGMENT_MAX = 2, 5

# Known vendor API hosts -> trust-domain label. Anything else aggregates by
# its endpoint host with the port stripped: two ports on one host are the
# SAME trust domain (a port is not an isolation boundary), and two seats on
# the same vendor are the same trust domain no matter how they are named.
VENDOR_TRUST_DOMAINS = {
    "api.anthropic.com": "anthropic",
    "api.openai.com": "openai",
}

# Every spelling of the local machine is one trust domain: a loopback address
# is not an isolation boundary either, so 'localhost', '127.0.0.1' and '::1'
# must never look like three distinct parties.
_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}
_LOOPBACK_DOMAIN = "loopback"


def normalize_host(endpoint_host: str) -> str:
    """Canonical host label for an endpoint: lowercase, trailing dot stripped,
    port removed, IPv6-safe. Accepts a bare host ('api.openai.com', '::1'),
    a host:port ('api.openai.com:443', '[::1]:8080') or a full URL. Returns
    '' only when there is genuinely no host to name."""
    raw = (endpoint_host or "").strip()
    if not raw:
        return ""
    # urlsplit only extracts host/port when it sees an authority; give it one.
    # A bare 'api.openai.com:443' looks like a scheme, so we always prefix //.
    probe = raw if "://" in raw else "//" + raw
    try:
        parsed = urlsplit(probe)
        host = parsed.hostname  # already strips [] from IPv6 and the :port
    except ValueError:
        host = None
    if not host:
        # urlsplit could not find an authority (e.g. a lone '::1' with no
        # brackets parses as a scheme-relative path). Fall back to the raw
        # value with a trailing :port heuristic that leaves IPv6 intact.
        host = raw
        if host.count(":") == 1:  # host:port, never bare IPv6 (>=2 colons)
            host = host.rsplit(":", 1)[0]
    return host.rstrip(".").lower()


def trust_domain(endpoint_host: str) -> str:
    """Trust-domain label for an endpoint host (rule above; documented in
    docs/fragmentation.md). Host is normalized (lowercase, trailing dot and
    port stripped, IPv6-safe); every loopback spelling collapses to one
    domain; known vendors collapse to the vendor label."""
    host = normalize_host(endpoint_host)
    if host in _LOOPBACK_HOSTS:
        return _LOOPBACK_DOMAIN
    return VENDOR_TRUST_DOMAINS.get(host, host or "unknown")


def load_fragments(d: Path) -> list[dict]:
    """Fragment declarations for one example directory.

    Explicit form (masking_plan.yaml):
        fragments:
          - id: pricing
            payload: provider_a_payload.txt
            mock_answer: mock_answer_a.txt
    Legacy form (no `fragments` key): the original two-seat convention,
    byte-identical behaviour so existing examples and signed fixtures are
    untouched.

    Fail-close: bad ids, duplicates, missing payload files, or a count
    outside 2..5 abort before anything else runs (exit 2 semantics).
    """
    import yaml
    plan_path = d / "masking_plan.yaml"
    plan = yaml.safe_load(plan_path.read_text(encoding="utf-8")) if plan_path.exists() else {}
    declared = (plan or {}).get("fragments")
    if not declared:
        return [
            {"id": "mock_provider_a", "payload": d / "provider_a_payload.txt",
             "mock_answer": d / "mock_answer_a.txt"},
            {"id": "mock_provider_b", "payload": d / "provider_b_payload.txt",
             "mock_answer": d / "mock_answer_b.txt"},
        ]
    if not (FRAGMENT_MIN <= len(declared) <= FRAGMENT_MAX):
        raise SystemExit(
            f"masking_plan.yaml declares {len(declared)} fragments; supported "
            f"range is {FRAGMENT_MIN}..{FRAGMENT_MAX} in this version "
            "(see docs/fragmentation.md)")
    frags, seen = [], set()
    for i, item in enumerate(declared):
        if not isinstance(item, dict) or "id" not in item or "payload" not in item:
            raise SystemExit(f"fragments[{i}] must declare `id` and `payload`")
        fid = str(item["id"])
        if not re.match(r"^[a-z][a-z0-9_-]{0,31}$", fid):
            raise SystemExit(f"fragments[{i}].id {fid!r} must match [a-z][a-z0-9_-]{{0,31}}")
        if fid in seen:
            raise SystemExit(f"duplicate fragment id {fid!r} in masking_plan.yaml")
        seen.add(fid)
        payload = d / str(item["payload"])
        if not payload.exists():
            raise SystemExit(f"fragment {fid!r}: payload file not found: {payload}")
        answer = d / str(item["mock_answer"]) if item.get("mock_answer") else None
        frags.append({"id": fid, "payload": payload, "mock_answer": answer})
    return frags


def example_paths(example_dir: str | Path) -> dict:
    requested = Path(example_dir)
    if not requested.exists():
        raise SystemExit(f"example path not found: {requested}")
    d = requested.parent if requested.is_file() else requested
    original = requested if requested.is_file() else d / "input.original.example.txt"
    fragments = load_fragments(d)
    return {
        "dir": d,
        "original": original,
        "masking_plan": d / "masking_plan.yaml",
        "local_only": d / "local_only.json",
        "fragments": fragments,
        "payloads": {f["id"]: f["payload"] for f in fragments},
        "answers": {f["id"]: f["mock_answer"] for f in fragments
                    if f["mock_answer"] is not None},
        "rehydrated": d / "final_rehydrated_answer.txt",
        "receipt": d / "receipt.json",
        "receipt_local": d / "receipt.local.json",
    }


def load_local_only(paths: dict) -> dict:
    return json.loads(paths["local_only"].read_text(encoding="utf-8"))


def load_masking_plan(paths: dict) -> dict:
    import yaml
    return yaml.safe_load(paths["masking_plan"].read_text(encoding="utf-8"))


def load_run_inputs(paths: dict) -> dict:
    """Read every input a live run consumes from disk EXACTLY ONCE.

    Returns the immutable in-memory buffers that the leak gate, consent
    preflight, wire transmission, exposure/hash accounting and receipt body
    all share. Nothing downstream re-opens these files, so overwriting a
    payload after this call cannot make the receipt disagree with the bytes
    that were actually transmitted (single-read TOCTOU fix).
    """
    return {
        "original": read_text(paths["original"]),
        "payloads": {fid: read_text(path)
                     for fid, path in paths["payloads"].items()},
        "local_only": load_local_only(paths),
        "masking_plan": load_masking_plan(paths),
    }


def exposure_view_from_texts(original: str, payload_texts: dict[str, str]) -> dict:
    """Character-count exposure accounting (RECEIPT_STANDARD section 1) over
    already-loaded, already-normalized text. `run-live` loads each payload
    from disk exactly once and passes the SAME buffer here that it hashes,
    gates and transmits — no re-read can race the numbers."""
    n = len(original)
    if n == 0 and any(payload_texts.values()):
        # Fail-close: a zero denominator would report 0.0 exposure for
        # payloads that plainly disclose content — refuse to account at all.
        raise SystemExit("original input is empty but payloads are not; "
                         "exposure accounting would under-report — aborting")
    per = {}
    saw_full = False
    for provider, payload in payload_texts.items():
        ratio = round(len(payload) / n, 6) if n else 0.0
        per[provider] = {"chars": len(payload), "exposure_ratio": ratio,
                         "payload_sha256": text_sha256(payload)}
        if payload == original:
            saw_full = True
    return {"original_chars": n, "providers": per,
            "max_single_provider_exposure": round(
                max((v["exposure_ratio"] for v in per.values()), default=0.0), 6),
            "no_single_provider_saw_full": not saw_full}


def exposure_view(paths: dict) -> dict:
    """Path-based wrapper (reads from disk). Kept for run_mock/demo/preview."""
    return exposure_view_from_texts(
        read_text(paths["original"]),
        {p: read_text(path) for p, path in paths["payloads"].items()})


def leak_findings_from_texts(local_only: dict, payload_texts: dict[str, str]) -> list[str]:
    """Exact-substring leak check over already-loaded text.

    One rule, one implementation: the preview gate and the transmission gate
    must never disagree, and — since `run-live` passes the very buffers it is
    about to transmit — the gate can never inspect different bytes than the
    ones that leave the machine. P0 limitation: exact substrings >= 4 chars
    only — paraphrased or partial leakage is NOT detected (docs/masking_levels.md).
    """
    lowered = {p: text.lower() for p, text in payload_texts.items()}
    findings = []
    for fld, value in local_only.items():
        needle = (value if isinstance(value, str) else str(value)).lower().strip()
        if len(needle) < 4:
            continue  # too short to be a meaningful leak signal
        for provider, text in lowered.items():
            if needle in text:
                findings.append(f"{fld!r} value found in {provider} payload")
    return findings


def leak_findings(paths: dict) -> list[str]:
    """Path-based wrapper (reads from disk). Kept for `apl mask`/preview."""
    return leak_findings_from_texts(
        load_local_only(paths),
        {p: read_text(path) for p, path in paths["payloads"].items()})


def load_policy_manifest() -> dict:
    return json.loads(_resources.read_spec_text("demo_policy_manifest.json"))
