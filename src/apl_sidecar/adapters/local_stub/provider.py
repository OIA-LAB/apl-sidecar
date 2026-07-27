# SPDX-License-Identifier: FSL-1.1-ALv2
"""Local stub — deterministic placeholder for local-model execution.

In enterprise deployments this seat is taken by a customer-controlled local
model endpoint. In P0 it simply echoes a deterministic marker so flows that
route a fragment to "local" have a well-defined, offline behavior.
"""
from __future__ import annotations

import hashlib

PROVIDER_ID = "local_stub"


def respond(prompt_text: str) -> str:
    digest = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()[:12]
    return f"[local-stub] processed locally ({digest})"
