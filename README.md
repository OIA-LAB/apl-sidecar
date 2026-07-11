# APL Sidecar

**Private Mode for AI.** APL runs minimal-exposure AI sessions so no single
provider needs the whole picture. Preview and approve what leaves your machine,
split sensitive context, reassemble locally, then clean up or retain a signed
receipt as advanced trust evidence. See [Private Mode for AI](docs/private_mode.md).

Private mode is a mental model, not a zero-trace promise: APL cannot control
provider retention or hide account, IP, and network metadata. The local
OpenAI-compatible proxy is an integration surface, not the product itself.
Opening a private browser window does not hide what your prompt reveals.

APL Sidecar is an open-source local playground for AI task exposure control.

It is designed for sensitive AI tasks where the content itself is valuable:

- a startup or side-project idea you have not announced;
- a codebase, repo, or product context you do not want one AI provider to fully understand.

APL Sidecar helps you preview:

- what stays local;
- what each provider sees;
- whether any single provider saw the full context;
- whether the signed receipt can be verified later.

P0 uses user-guided masking, mock providers, local rehydration, signed receipts, exposure accounting, and tamper-fail verification.

It does not claim zero leakage, provider non-retention, network anonymity, automatic semantic decomposition, or production-grade enterprise routing.

> Don't paste the whole idea. Don't expose the whole repo. Keep a receipt.

## How it works

```
Your sensitive task
   │
   ├── local-only fields ──────────────► never leave your machine
   │
   ├── Provider A payload ─► mock provider A ─┐
   ├── Provider B payload ─► mock provider B ─┤
   │                                          ▼
   └──────────────► local rehydration ◄───────┘
                          │
                          ▼
              signed exposure receipt
        (who saw what, how much, verifiable,
             tamper-evident, chainable)
```

No login. No API key. No network. Mock/offline by default.

## Quick start

```bash
pip install cryptography pyyaml

python cli/apl.py preview examples/00_private_idea
python cli/apl.py run-mock examples/00_private_idea
python cli/apl.py rehydrate examples/00_private_idea
python cli/apl.py inspect examples/00_private_idea/receipt.json
python cli/apl.py verify examples/00_private_idea/receipt.json
```

And for the code-context scenario:

```bash
python cli/apl.py preview examples/01_private_code_context
python cli/apl.py run-mock examples/01_private_code_context
python cli/apl.py rehydrate examples/01_private_code_context
python cli/apl.py inspect examples/01_private_code_context/receipt.json
python cli/apl.py verify examples/01_private_code_context/receipt.json
```

Interactive playground (local, offline):

```bash
python cli/apl.py playground
# open http://127.0.0.1:8791/app/local_playground/ — loopback only, zero network calls
```

Tamper check — change ONE byte of a receipt and verification must fail:

```bash
python cli/apl.py verify examples/00_private_idea/tampered_receipt.example.json
# -> Verification failed: receipt was modified or signature is invalid.
```

## What P0 is (and is not)

P0 **is**: user-guided masking, provider payload preview, local-only field
tracking, mock provider responses, local rehydration, character-count exposure
accounting, Ed25519-signed receipts, receipt chaining, tamper-fail verification,
fully offline reproducibility.

P0 **is not**: zero leakage, cryptographic secrecy of task content, provider
non-retention, network or account anonymity, automatic semantic decomposition,
automatic sensitive-field detection, or production-grade enterprise routing.
See [docs/not_claims.md](docs/not_claims.md) for the full boundary.

**P0 limitation statement:** P0 uses user-guided masking and curated provider
payloads. Verification, signing, receipt chaining, and exposure accounting are
real. Automatic semantic decomposition is a roadmap item, not a P0 claim.

## Modes

| Mode          | Description                                      | API key | Network | Default      |
| ------------- | ------------------------------------------------ | ------- | ------- | ------------ |
| `mock`        | Offline fixture-based provider responses         | No      | No      | **Yes**      |
| `hosted-live` | OIA-controlled backend relay using provider pool | No      | Yes     | Website only |
| `byok`        | Bring your own API key                           | Yes     | Yes     | No           |
| `enterprise`  | Production policy, routing, audit, governance    | Depends | Depends | No           |

The public repo defaults to mock/offline and is not bound to any live vendor.
See [docs/experience_modes.md](docs/experience_modes.md) and
[docs/hosted_live_demo.md](docs/hosted_live_demo.md).

## Enterprise and Vertical Workflows

APL Sidecar is the open-source entry point.

Enterprise and vertical workflows are handled through APL Enterprise Gateway, including:

- patent and invention disclosure workflows;
- supplier negotiation and procurement analysis;
- financial and board-level document workflows;
- medical research and sensitive case summarization;
- legal, compliance, and internal governance workflows.

These workflows require production policy enforcement, provider governance, deployment controls, audit evidence, and workflow-specific evidence packs.

The public repo does not include enterprise routing logic, production decomposition rules, private workflow templates, or customer data.

See [docs/enterprise_gateway.md](docs/enterprise_gateway.md).

## Roadmap: A2A

APL for A2A is a roadmap direction for extending task exposure receipts from human-to-model workflows to agent-to-agent workflows. P0 does not support A2A.

See [docs/roadmap_a2a.md](docs/roadmap_a2a.md).

## License

MIT — see [LICENSE](LICENSE). All example content is fictional and synthetic.
