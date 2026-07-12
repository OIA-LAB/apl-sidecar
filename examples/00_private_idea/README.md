# Example 00 — Private Idea

> All content in this example is **fictional and synthetic**. "Quietloom" and
> every detail about it are invented for demonstration.

## Why the original task is sensitive

The natural prompt is: *"Here is my whole startup idea — help me position and
launch it."* Pasting that gives one provider the project name, the unique
mechanism, the pricing, the go-to-market channel, and the founder's filing
constraints in a single request. A disposable account does not help: the
**idea itself** is the sensitive asset, and full-context exposure is the risk.

## How APL splits it for this demo

- `local_only.json` — name, mechanism, market, pricing, GTM channel, moat,
  founder notes. These never leave the machine; only their hashes enter the
  receipt.
- `provider_a_payload.txt` — a generalized positioning/adoption question
  (no name, no differentiator, no business model).
- `provider_b_payload.txt` — a README/landing-structure task (no idea, no
  pricing, no customer names).
- `mock_answer_*.txt` — curated offline responses.
- `final_rehydrated_answer.txt` — the answers merged with the local-only
  context **locally**. AI still helps with structure, positioning, and
  clarity without any single provider seeing the full idea.

Run it:

```bash
apl preview   examples/00_private_idea
apl mask      examples/00_private_idea      # leak-check
apl run-mock  examples/00_private_idea
apl rehydrate examples/00_private_idea
```

## How the receipt is verified

```bash
apl inspect examples/00_private_idea/receipt.json
apl verify  examples/00_private_idea/receipt.json
# -> Signature verified. Receipt chain valid.

apl verify  examples/00_private_idea/tampered_receipt.example.json
# -> Verification failed: receipt was modified or signature is invalid.
```

The receipt records payload hashes, per-provider exposure ratios,
`no_single_provider_saw_full`, and the local-only field fingerprints — signed
with Ed25519. Change any byte and verification fails.

---

This example uses user-guided masking and curated provider payloads. P0
verification, signing, receipt chaining, and exposure accounting are real.
Automatic semantic decomposition is a roadmap item, not a P0 claim.
