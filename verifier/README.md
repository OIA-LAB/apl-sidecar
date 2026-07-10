# APL Receipt Verifier

Reference implementation of [RECEIPT_STANDARD.md](../RECEIPT_STANDARD.md).

```bash
# single receipt
python verifier/apl_verify.py examples/00_private_idea/receipt.json

# a chain, in order
python verifier/apl_verify.py \
    spec/conformance_vectors/valid_chain/receipt_001.json \
    spec/conformance_vectors/valid_chain/receipt_002.json

# tampered receipt must fail (exit code 1)
python verifier/apl_verify.py \
    spec/conformance_vectors/tamper_vectors/tamper_payload_changed.json
```

Output contract:

- valid: `Signature verified. Receipt chain valid.` (exit 0)
- invalid: `Verification failed: receipt was modified or signature is invalid.`
  plus a reason in parentheses (exit 1)

Public keys are resolved by `signing_key_id`: `keys/<id>.pem` (your local
demo key, gitignored) first, then `spec/<id>.pem` (the repo demo public key
used for the committed fixtures). Override with `--pubkey path.pem`.

Only the `cryptography` package is required. No network.
