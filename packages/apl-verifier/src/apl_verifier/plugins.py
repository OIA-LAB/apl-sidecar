# SPDX-License-Identifier: Apache-2.0
"""Planner / provider plugin interface types — INTERFACE ONLY, zero behaviour.

These Protocols define the shape a planner or provider adapter must satisfy to
interoperate with the verification layer. There is deliberately no
implementation here: automatic decomposition, planning, evaluation and
provider transport all live outside this Apache-2.0 package. This module exists
so third parties can type-check their own adapters against a stable, permissively
licensed contract.
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ProviderPlugin(Protocol):
    """Minimal contract for a provider adapter, as seen by the verifier layer.

    Only the attributes the receipt/trust accounting reads are declared. No
    transport, credential or planning method is part of this interface.
    """

    #: Canonical endpoint host (e.g. "api.openai.com"); feeds trust_domain().
    endpoint_host: str

    def provider_id(self) -> str:
        """Stable identifier for this provider seat."""
        ...


@runtime_checkable
class PlannerPlugin(Protocol):
    """Contract a planner must satisfy to hand fragments to the verifier layer.

    The planning logic itself is out of scope for this package; only the shape
    of what it produces is declared here so a receipt can be checked against a
    planner's declared seat set without importing any planner implementation.
    """

    def seat_ids(self) -> list[str]:
        """The seat identifiers this plan will populate."""
        ...
