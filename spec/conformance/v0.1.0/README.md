# v0.1.0 conformance vectors (frozen)

These files are extracted verbatim from the `v0.1.0` release tag and are
**frozen** — do not edit them. They are the permanent backward-compatibility
gate: `apl-verifier` (0.2.0 and later) must verify `receipt.json` against
`apl-oss-demo-key.pem` and must reject `tampered_receipt.json`.

| File | Source (v0.1.0 tag) | Role |
| --- | --- | --- |
| `receipt.json` | `examples/00_private_idea/receipt.json` | real signed v0.1.0 receipt — MUST verify |
| `tampered_receipt.json` | `examples/00_private_idea/tampered_receipt.example.json` | tampered twin — MUST be rejected |
| `apl-oss-demo-key.pem` | `spec/apl-oss-demo-key.pem` | v0.1.0 demo PUBLIC key (byte-identical to the current one) |

Enforced by `packages/apl-verifier/tests/test_v010_conformance.py`.

Licensed CC BY 4.0 as part of the specification layer (see
[`../../LICENSE`](../../LICENSE)).
