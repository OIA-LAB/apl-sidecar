# Example 01 — Private Code / Repo Context

> All content in this example is **fictional and synthetic**. The repo, the
> code, the "key", the customer, and the roadmap are invented. The API key
> string is a fake placeholder.

## Why the original task is sensitive

The natural prompt is: *"Here is my repo context — help me debug and fix the
docs."* That single paste carries the repo name, the file tree, a committed
secret-like value, a customer name, the internal architecture note that is
believed to be a differentiator, and the competitive roadmap. A disposable
account does not help: the **code context itself** is the sensitive asset.

## How APL splits it for this demo

- `local_only.json` — repo name, tree, secret-like strings, customer names,
  roadmap, architecture notes, product direction. Never leave the machine.
- `provider_a_payload.txt` — a minimal bug reproduction: 10-line snippet +
  error message. No tree, no roadmap, no customer, no secrets.
- `provider_b_payload.txt` — a generic README/API documentation task.
- `final_rehydrated_answer.txt` — provider outputs mapped back onto the real
  repo context **locally**. AI still helps debug and improve documentation
  without seeing the whole repo.

Run it:

```bash
python cli/apl.py preview   examples/01_private_code_context
python cli/apl.py mask      examples/01_private_code_context   # leak-check
python cli/apl.py run-mock  examples/01_private_code_context
python cli/apl.py rehydrate examples/01_private_code_context
```

## How the receipt is verified

```bash
python cli/apl.py inspect examples/01_private_code_context/receipt.json
python cli/apl.py verify  examples/01_private_code_context/receipt.json
# -> Signature verified. Receipt chain valid.

python cli/apl.py verify  examples/01_private_code_context/tampered_receipt.example.json
# -> Verification failed: receipt was modified or signature is invalid.
```

---

This example uses user-guided masking and curated provider payloads. P0
verification, signing, receipt chaining, and exposure accounting are real.
Automatic repo understanding and semantic decomposition are roadmap items,
not P0 claims.
