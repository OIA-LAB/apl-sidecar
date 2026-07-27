# SPDX-License-Identifier: FSL-1.1-ALv2
"""Minimal JSON POST transport for BYOK adapters. Stdlib only, fail-close.

Design rules (mirrors the receipt philosophy: evidence over trust):
- hard timeout and response size cap — a hung or oversized response is a failure;
- secrets passed by the caller are scrubbed from every raised message, so an
  API key can never leak through a traceback, log line, or receipt;
- no retries — a live call either happened once or it did not, which keeps
  provider_events honest.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

DEFAULT_TIMEOUT_S = 60.0
MAX_RESPONSE_BYTES = 2 * 1024 * 1024  # 2 MiB


class ByokConfigError(ValueError):
    """Adapter is not configured correctly (missing key, model, or URL)."""


class TransportError(RuntimeError):
    """Network call failed. Message is always secret-scrubbed."""


def _scrub(message: str, secrets: tuple[str, ...]) -> str:
    for secret in secrets:
        if secret:
            message = message.replace(secret, "[redacted]")
    return message


def post_json(url: str, headers: dict[str, str], body: dict[str, Any],
              timeout: float = DEFAULT_TIMEOUT_S,
              max_bytes: int = MAX_RESPONSE_BYTES,
              secrets: tuple[str, ...] = ()) -> dict[str, Any]:
    """POST a JSON body, return the parsed JSON response. Raises TransportError."""
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        url, data=data, method="POST",
        headers={**headers, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(max_bytes + 1)
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read(500).decode("utf-8", errors="replace")
        except Exception:  # noqa: BLE001 — never let error reporting raise
            pass
        raise TransportError(_scrub(
            f"provider returned HTTP {exc.code}: {detail}".strip(), secrets)) from None
    except Exception as exc:  # URLError, timeout, ConnectionError, ...
        raise TransportError(_scrub(f"request failed: {exc}", secrets)) from None
    if len(raw) > max_bytes:
        raise TransportError(f"response exceeded {max_bytes} bytes")
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TransportError(_scrub(f"response is not valid JSON: {exc}", secrets)) from None
    if not isinstance(parsed, dict):
        raise TransportError("response JSON is not an object")
    return parsed
