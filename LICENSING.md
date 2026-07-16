# Licensing

APL Sidecar is licensed in layers. Each layer has one license, chosen for what
that layer is for.

| Layer | What it covers | License |
| --- | --- | --- |
| Specification | `spec/` (receipt profile, field definitions, schemas, conformance vectors) and `RECEIPT_STANDARD.md` | CC BY 4.0 |
| Verifier / SDK | `packages/apl-verifier/` (offline receipt verification, trust-domain rule, plugin interface types) | Apache-2.0, permanently |
| Runtime (v0.2+) | everything else in this repository | FSL-1.1-ALv2 — Fair Source; each released version converts to Apache-2.0 two years after its release date |
| Runtime (v0.1.0) | the v0.1.0 release | MIT — historical release, rights unchanged |
| Planner / Evaluator | not in this repository | commercial product, distributed separately |

The full texts are in [`LICENSE`](LICENSE) and [`LICENSES/`](LICENSES/); the
specification text is in [`spec/LICENSE`](spec/LICENSE); the verifier text is in
[`packages/apl-verifier/LICENSE`](packages/apl-verifier/LICENSE).

## FAQ

**Why FSL for the runtime?**
I am one person. FSL-1.1-ALv2 lets me keep the runtime source open and usable
for internal use, evaluation, research, and professional services, while
reserving the right to be the one who offers it as a competing commercial
product. Every released version automatically becomes Apache-2.0 two years
after its release, so nothing stays restricted forever.

**Why is the verifier permanently open?**
Verification must never depend on my licensing choices. Anyone should be able
to check an APL receipt — including receipts I did not produce — without asking
me and without a runtime license. So `apl-verifier` is Apache-2.0 and stays
that way. The dependency direction is one-way: the runtime depends on the
verifier, never the reverse.

**Does this change anything for v0.1.0 users?**
No. v0.1.0 was released under MIT. That release and its rights are unchanged; a
later version being under a different license does not reach back to it. If you
depend on v0.1.0 under MIT, you keep those terms.

**Can I use the spec to build my own implementation?**
Yes. The specification is CC BY 4.0 — reuse it with attribution. The
conformance vectors under `spec/conformance_vectors/` are the shared reference
your implementation can test against.
