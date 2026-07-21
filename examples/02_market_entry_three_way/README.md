# Example 02 — Market Entry, Three-Way Split

> All content in this example is **fictional and synthetic**. "Brimshade
> Labs", "Petrelwing", the chains, the costs, and the dates are invented.

This is the first example with a declared fragment plan (`fragments:` in
`masking_plan.yaml`): three self-contained workstreams — `pricing`,
`channel`, `risk` — each sent to its own seat.

## Why three fragments here

The three workstreams are separable questions: each is useful on its own
and none needs the others' context to be answerable. That is what makes a
task a good candidate for fragmentation — not every task is.

Splitting lowers the **measurable per-seat disclosure share** (signed into
the receipt). It does not by itself guarantee lower reconstruction risk —
a short fragment can still reveal the whole intent — and it widens the set
of parties that see something. See [docs/fragmentation.md](../../docs/fragmentation.md)
for the honest trade-off, including what happens when several seats
resolve to the **same trust domain** (their exposure aggregates; the
receipt records it).

## Run it

```bash
apl preview   examples/02_market_entry_three_way
apl mask      examples/02_market_entry_three_way      # leak-check
apl run-mock  examples/02_market_entry_three_way
apl rehydrate examples/02_market_entry_three_way

# live (BYOK), every seat named explicitly:
apl run-live examples/02_market_entry_three_way \
    --seat pricing=anthropic --seat channel=openai --seat risk=openai
```

Note the last command on purpose sends two fragments to the same vendor:
the preflight and the receipt will show `channel` + `risk` aggregated into
one trust domain — fragment count alone does not reduce what that provider
receives.

## No static receipt shipped

Unlike `00_private_matter` and `01_private_code_context`, this scenario ships
**no committed `receipt.json`** (and no `tampered_receipt.example.json` or
`inspect.expected`). It is a run-mock / run-live scenario: **you** generate the
receipt by running `apl run-mock` (offline) or `apl run-live` (BYOK) above,
which writes it to `apl-out/` (or your `--output` dir). There is nothing to
`apl verify` here until you have run it. The signing, verification, receipt
chaining, and exposure accounting exercised by that run are real.

---

This example uses user-guided masking and curated provider payloads.
Automatic semantic decomposition is a roadmap item, not a claim.
