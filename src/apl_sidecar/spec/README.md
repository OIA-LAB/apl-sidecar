# APL Sidecar Specification

This directory is the **specification layer** of APL Sidecar: the receipt
profile, field definitions, machine schemas, and conformance test vectors that
define what a valid APL receipt is, independent of any implementation.

## Contents

| Path | What it is |
| --- | --- |
| [`../RECEIPT_STANDARD.md`](../RECEIPT_STANDARD.md) | Receipt profile — canonical serialization, field semantics, verification rules (narrative spec). |
| `receipt.schema.json` | Machine-readable receipt field definitions. |
| `policy_manifest.schema.json` | Policy manifest field definitions. |
| `demo_policy_manifest.json` | Example policy manifest. |
| `conformance_vectors/valid_chain/` | Valid receipt chain — MUST verify. |
| `conformance_vectors/tamper_vectors/` | Tampered receipts — MUST be rejected. |
| `apl-oss-demo-key.pem` | Demo **public** key that signs the vectors above. |

### Conformance vectors are the single source of truth

`conformance_vectors/` is the one authoritative set of test vectors. The
verifier's tests reference these files directly from a checkout — a conforming
implementation is one that accepts every `valid_chain` receipt and rejects
every `tamper_vectors` receipt. Do not fork or duplicate them.

## License

**The specification layer is licensed CC BY 4.0.** The full text is in
[`LICENSE`](LICENSE). This directory-level notice covers every file in `spec/`,
including the JSON and YAML vectors and schemas.

The vectors and schemas carry **no inline license header or `license` field**
on purpose: a receipt's canonical bytes are what gets hashed and signed, so
injecting a footer or a license key would break verification. Attribution for
those files is provided here at the directory level instead.

> Copyright 2026 Yu-Chia Chang (張育嘉). Licensed under CC BY 4.0.
