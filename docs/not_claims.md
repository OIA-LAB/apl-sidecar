# What APL Sidecar Does NOT Claim

This is the product claim boundary. Anything not listed as a claim in the
README is not a claim. The list below is explicit because privacy tools die
by overclaiming.

## APL Sidecar P0 must not be described as providing

- zero leakage;
- cryptographic secrecy of task content;
- provider non-retention (we cannot attest what a provider stores);
- network anonymity (your IP and TLS metadata are out of scope);
- account anonymity (your provider account is out of scope);
- automatic semantic decomposition (P0 masking is user-guided + curated);
- automatic sensitive-field detection (roadmap, see masking_levels.md);
- production-grade enterprise routing or policy enforcement;
- legal, medical, financial, or investment advice;
- A2A (agent-to-agent) support;
- that the hosted demo is safe for real secrets;
- that free provider APIs are stable or unlimited.

## Correct framing

| Use                                                | Avoid                             |
| -------------------------------------------------- | --------------------------------- |
| "APL Sidecar reduces full-context exposure."       | "APL guarantees no intent leakage." |
| "No single provider saw the full task context."    | "No provider can infer anything."   |
| "Verifiable exposure receipt."                     | "Magic privacy."                    |

## What the receipt actually proves

The receipt proves **what was sent**: which payload went to which provider,
what fraction of the original input each provider received (character count),
that no single provider payload equals the full context, and that this record
has not been modified since signing.

It does not prove what any provider did with what it received.
