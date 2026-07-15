# APL Receipt Verifier (moved)

The verifier now lives in its own permanently Apache-2.0 package:
[`packages/apl-verifier/`](../packages/apl-verifier/README.md).

`verifier/apl_verify.py` in this directory is a **deprecated compatibility
shim** (removal in v0.3). It re-exports the package API and keeps the old
auto key-resolution behaviour for existing callers.

## Use the package

```bash
pip install apl-verifier

# --pubkey is required: the caller chooses which key to trust
apl-verify examples/00_private_idea/receipt.json --pubkey spec/apl-oss-demo-key.pem

# a chain, in order
apl-verify \
    spec/conformance_vectors/valid_chain/receipt_001.json \
    spec/conformance_vectors/valid_chain/receipt_002.json \
    --pubkey spec/apl-oss-demo-key.pem
```

From the APL runtime, `apl verify <receipt.json>` resolves the demo key for you
(user key dir, then the packaged `spec/` demo public key), then calls the same
package.

Output contract:

- valid: `Signature verified. Receipt chain valid.` (exit 0)
- invalid: `Verification failed: receipt was modified or signature is invalid.`
  plus a reason in parentheses (exit 1)

Only the `cryptography` package is required. No network.
