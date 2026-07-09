# Exposure Model

## The risk APL measures

The risk is not only data leakage. The risk is **full-context exposure**:
one provider seeing enough of your task to reconstruct the whole intent —
the idea, the strategy, the roadmap, the codebase shape.

## P0 exposure accounting

P0 exposure is character-count based and deliberately simple:

```
provider_exposure_ratio = characters_sent_to_provider / characters_in_original_input
```

Per receipt, APL records:

- exposure ratio per provider (`single_provider_exposure`);
- the worst single provider (`max_single_provider_exposure`);
- whether any provider payload equals the full context
  (`no_single_provider_saw_full`);
- hashes of local-only fields (`local_only_hashes`) — content never leaves,
  only fingerprints enter the receipt.

## What this metric is and is not

It **is**: deterministic, recomputable from the receipt by anyone, and honest
about magnitude ("provider A received 23% of the characters").

It **is not**: a semantic privacy score. 10% of characters can carry 90% of
the meaning if you mask badly. That is why P0 masking is user-guided and why
the docs never translate exposure ratio into a "protection level".

We do not publish unstable internal metrics, semantic privacy scores, or
mathematical privacy guarantees.

## Threat framing in one line

An incognito window changes who you appear to be.
APL changes **how much of your task any single provider gets to see** — and
gives you a signed, tamper-evident record of it.
