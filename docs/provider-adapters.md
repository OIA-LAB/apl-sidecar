# Provider Adapters

APL's canonical adapter contract is `adapters.base.ProviderAdapter`. An adapter declares a stable `provider_id`, immutable capabilities, and a `complete(ProviderRequest) -> ProviderResponse` method.

Register adapters explicitly with `ProviderRegistry.register`. Duplicate IDs fail closed. The runtime does not discover or import unknown plugins automatically.

Offline adapters must declare `ProviderCapabilities(network=False)`. The default demo checks this capability before every call. A future network adapter must declare `network=True`; its CLI path must require explicit user opt-in and must never become the demo default.

The bundled fixture adapters in `adapters/mock.py` demonstrate the contract without credentials or network access.
