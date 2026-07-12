"""apl run-mock -- run mock providers offline, build and sign a receipt.

Zero network. Loads mock answers via the adapters, accounts exposure, signs a
receipt with your local demo key (auto-generated under gitignored keys/), and
writes receipt.local.json next to the example (the committed receipt.json is
the curated fixture signed by the repo demo key).
"""
from __future__ import annotations

import json
import time

from . import _common as c
from . import _signing

from adapters.base import ProviderRequest
from adapters.mock import default_registry


def build_receipt_body(paths: dict, responses: dict) -> dict:
    view = c.exposure_view(paths)
    local_only = c.load_local_only(paths)
    plan = c.load_masking_plan(paths)
    policy = c.load_policy_manifest()
    events, exposures = [], []
    for provider, info in view["providers"].items():
        resp = responses.get(provider)
        events.append({"provider_id": provider,
                       "payload_sha256": info["payload_sha256"],
                       "payload_chars": info["chars"],
                       "response_sha256": c.text_sha256(resp) if resp else None,
                       "event_type": "mock_response" if resp else "no_response"})
        exposures.append({"provider_id": provider,
                          "exposure_ratio": info["exposure_ratio"]})
    return {
        "run_id": c.new_ulid(),
        "task_type": plan["task_type"],
        "policy_id": policy["policy_id"],
        "provider_events": events,
        "local_only_hashes": [
            {"field": k, "sha256": c.text_sha256(json.dumps(v) if not isinstance(v, str) else v)}
            for k, v in sorted(local_only.items())],
        "single_provider_exposure": exposures,
        "max_single_provider_exposure": view["max_single_provider_exposure"],
        "no_single_provider_saw_full": view["no_single_provider_saw_full"],
        "prev_receipt_hash": None,
        "masking_level": "guided_curated_p0",
        "provenance": {
            "apl_sidecar_version": "0.1.0-draft",
            "receipt_schema_version": "0.1.0-draft",
            "policy_version": policy["policy_version"],
            "example_id": paths["dir"].name,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
    }


def run(example_dir: str) -> int:
    paths = c.example_paths(example_dir)
    registry = default_registry()
    responses = {}
    for provider in c.PROVIDERS:
        adapter = registry.get(provider)
        if adapter.capabilities.network:
            raise RuntimeError(f"offline mock command rejected network adapter: {provider}")
        response = adapter.complete(ProviderRequest(
            prompt=c.read_text(paths["payloads"][provider]), model=adapter.model,
            fixture_dir=paths["dir"], metadata={"mode": "offline-mock"}))
        responses[provider] = response.text
        print(f"[{provider}] mock response loaded "
              f"({len(responses[provider])} chars) -- no network call made")
    key, key_id = _signing.ensure_local_keypair()
    receipt = _signing.sign_receipt(build_receipt_body(paths, responses), key, key_id)
    out = paths["receipt_local"]
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n",
                   encoding="utf-8")
    print(f"\nSigned receipt written: {out}")
    print(f"receipt_hash: {receipt['receipt_hash']}")
    print(f"Verify it:    apl verify {out}")
    return 0
