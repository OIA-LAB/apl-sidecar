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

**What patent license do I get during the FSL period?**
For the first two years after a runtime version is made available, the patent
license is the narrow FSL Patents grant — limited to a Permitted Purpose, with a
broad termination trigger. Two years after that version's release date, its
Grant of Future License takes effect and you receive the full Apache-2.0
Section 3 patent license for that version. The two periods run in sequence, not
in conflict. The licensor currently holds no issued patents; the patent clauses
grant whatever the licensor may hold and are not a representation that any
patent covers the Software.

**If the FSL patent license is terminated, does that kill my future Apache-2.0 patent rights?**
No. The FSL Patents termination, if triggered, ends only the patent license
under the FSL-period License Grant. It does not revoke the Apache-2.0 Future
License, which is granted separately and irrevocably now and takes effect on the
second anniversary of each version's release date. The FSL-period grant and the
Apache-2.0 Future License are two independent grants; terminating the first does
not reach the second.
