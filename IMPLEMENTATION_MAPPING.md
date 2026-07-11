# Developer-First Launch Implementation Mapping

This mapping follows `CURRENT_REPO_MAP.md`. Existing paths remain canonical; proposed work-order paths are capability labels only.

| Requested capability | Existing path | Current status | Planned change | Risk |
| --- | --- | --- | --- | --- |
| `apl demo` | `cli/apl.py`, `cli/commands/run_mock.py`, `rehydrate.py` | missing as one command | add thin `cli/commands/demo.py` orchestration that invokes canonical adapters, receipt signing, verifier, stitch artifact, renderer, and assessment | medium |
| Provider View | `examples/00_private_idea/`, `app/local_playground/` | static views exist | generate isolated per-run views inside a static `exposure.html`; reuse scenario data and escape all content | medium |
| Exposure HTML | `app/local_playground/` and `cli/commands/_common.py` | generated artifact missing | add a renderer module under `cli/commands/` or adjacent presentation boundary; no runtime duplication | medium |
| Receipt verify | `verifier/apl_verify.py`, `cli/commands/verify.py` | exists | reuse unchanged as canonical verification path; demo calls it directly | low |
| Tamper demo | tamper vectors and `verifier/apl_verify.py` | command missing | add `break-receipt` that copies receipt, changes one meaningful field, invokes canonical verifier, and preserves original | low |
| Assessment | documentation only | missing | add deterministic, explicitly exploratory offline assessment derived from disclosed fixture text; output required fields without a security verdict | medium |
| README | `README.md` | exists | revise to required developer-first order while preserving factual boundaries and linking deeper docs | medium |
| `apl preview` | `cli/commands/preview.py` | exists for directories | retain directory contract; add warnings, residual-risk language, and token estimates; optionally accept scenario/task mapping only through the same loader | medium |
| `apl run` | `run-mock.py` | equivalent partial command | add compatibility command that defaults to the canonical offline demo path; reject network providers unless future explicit support exists | medium |
| `apl inspect` | `cli/commands/inspect.py` | receipt-only | extend to accept an output directory and list/display its three artifacts; preserve receipt behavior | low |
| `apl --help` | `cli/apl.py` | missing successful help | add explicit help handling without replacing existing dispatch structure | low |
| Canonical receipt | `run_mock.py`, `_signing.py`, `spec/receipt.schema.json` | exists | reuse real signed receipt; copy it into output directory, adding optional metadata only if necessary and schema-compatible | high |
| Canonical provider abstraction | `adapters/base.py`, `registry.py`, `mock.py` | exists; old run path bypasses it | route demo and `run-mock` through registry adapters; keep legacy modules compatible | medium |
| Canonical local stitch | `final_rehydrated_answer.txt`, `rehydrate.py` | fixture-backed display | expose a reusable read/assemble boundary that copies the deterministic local artifact; label fixture-backed behavior honestly | medium |
| Exposure metrics | `_common.py`, `docs/exposure_model.md` | canonical character ratios exist | preserve receipt ratios; add separately labeled approximate token counts for the launch artifact | medium |
| Scenario pack | `examples/<scenario>/` | implicit format exists | document existing required files and add lightweight validation/metadata only if it does not duplicate current masking plan | low |
| OpenAI-compatible integration | `relay/openai_proxy.py` | exists and tested | document tested port/models after demo; optionally add `apl-demo` alias only if covered by tests | low |
| Public-claim tests | `tests/test_no_deprecated_terms.py` | partial gate exists | extend qualification-aware scanner for primary public-facing files | medium |
| Offline enforcement | adapters and proxy tests | partial | add demo-level socket guard test and registry capability assertions | medium |
| Demo media | none | missing | generate `assets/apl-demo.gif` from real terminal/demo artifacts; final frame shows actual canonical verifier failure | medium |
| Claims and limits | `docs/not_claims.md`, `SECURITY.md` | exists | retain canonical limits; add/readjust links and terminology after core demo | low |
| Provider adapter docs | protocol code only | missing focused guide | document minimal existing interface and explicit registration | low |
| Scenario docs | examples READMEs | partial | document contribution contract based on actual example layout | low |

## Implementation boundaries

1. No `src/` migration and no duplicate runtime.
2. The demo uses `ProviderRegistry` and offline `MockProviderAdapter` instances.
3. The existing Ed25519 signing and `verifier.apl_verify` path remain authoritative.
4. Generated `receipt.json` is the actual signed receipt, not a marketing projection.
5. Generated HTML and Markdown are presentation artifacts derived from the same run data.
6. Character exposure remains canonical; approximate token counts are labeled and kept separate from reconstruction risk.
7. Default commands cannot open external sockets; no silent live-provider fallback is added.
8. Existing example-directory commands and committed receipts remain compatible.

## Planned file discipline

For every changed existing file, the final report will record reason, preserved behavior, added behavior, and test coverage. New modules will be kept at current architectural boundaries (`cli/commands/`, `adapters/`, `tests/`, `docs/`, `assets/`) rather than mirroring the conceptual work-order tree.
