# apl-verifier

The independent verification layer for [APL Sidecar](../../README.md).

`apl-verifier` verifies APL receipts offline: schema shape, canonical hash,
Ed25519 signature, and chain continuity. It is fail-close — anything unexpected
is a verification failure. It contains the single trust-domain normalization
rule and interface-only plugin Protocols, and nothing else: no planning, no
automatic decomposition, no provider transport.

## Licensing

**This package is, and will remain, Apache-2.0.** It is distributed
independently of the APL runtime. Verification must stay permanently open so
anyone can check an APL receipt without depending on the runtime's licensing.
The dependency direction is one-way: the runtime depends on `apl-verifier`;
`apl-verifier` never imports the runtime.

## Install

```
pip install apl-verifier
```

Only dependency: `cryptography` (Ed25519).

## Use

```
apl-verify <receipt.json> [more_receipts_in_chain_order...] --pubkey key.pem
```

`--pubkey` is required: the caller decides which public key to trust. The tool
never searches repo-relative key directories, so a receipt can never steer it
to an attacker-chosen filesystem path.

Exit codes: `0` verified, `1` failed, `2` usage.

Library:

```python
from apl_verifier import verify_receipt, verify_chain, VerifyError
```
