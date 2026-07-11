# Implementation Report

Date: 2026-07-12 (Asia/Taipei)
Baseline commit: `3e9456ae318a4894c94cb0363063223cf809594a6`

## Outcome

The Developer-First Launch experience is implemented as a thin layer over the existing APL runtime. No repository reinitialization, structural migration, duplicate receipt, duplicate verifier, duplicate hash implementation, or separate demo runtime was introduced.

## Existing files modified

| File | Reason | Existing behavior preserved | New behavior | Test coverage |
| --- | --- | --- | --- | --- |
| `.gitignore` | Keep generated run artifacts out of Git | Existing ignores retained | Ignores `apl-out/` | Git status/diff inspection |
| `README.md` | Developer-first public launch | Factual product boundaries and links retained | Required hero, demo-first sequence, artifacts, tamper loop, integration, limits, extensions | public-claim gate; command smoke tests |
| `cli/apl.py` | Register launch commands through current dispatcher | All existing commands and direct script launch retained | `--help`, `demo`, `run`, `break-receipt` | `tests/test_demo.py`; baseline commands |
| `cli/commands/_common.py` | Reuse scenario loader for target CLI shape | Existing directory scenarios and character exposure unchanged | Task files inside scenario packs accepted; transparent token estimate helper | demo and task-file tests; original receipt tests |
| `cli/commands/run_mock.py` | Converge mock execution on canonical adapter interface | Output path, signing, receipt body and terminal behavior retained | Uses explicit `ProviderRegistry`; rejects network-capable adapters | adapter tests, existing receipt tests, full suite |
| `cli/commands/preview.py` | Add requested developer information | Exact payload/local-only preview and character ratios retained | Task-file support through loader, token estimates, warning and residual risk | task-file test; baseline preview |
| `cli/commands/inspect.py` | Inspect generated run directories | Receipt inspection remains unchanged | Lists three artifacts before inspecting canonical receipt | demo artifact test; baseline inspect |

## New implementation files

| File | Purpose | Canonical dependency |
| --- | --- | --- |
| `cli/commands/demo.py` | Offline orchestration and three-artifact renderer | ProviderRegistry, existing scenario loader, existing receipt builder/signing, canonical verifier |
| `cli/commands/break_receipt.py` | Safe one-field tamper copy and failure demonstration | `cli.commands.verify` / `verifier.apl_verify` |
| `tests/test_demo.py` | Artifact, offline, isolation, CLI, receipt and tamper gates | Real demo and verifier |
| `tests/test_public_claims.py` | Qualification-aware prohibited-claim gate | README/docs/examples/app public files |
| `assets/apl-demo.gif` | Eight-frame actual CLI transcript; final beat is verifier failure | Verified demo/tamper output |
| `docs/claims-and-limits.md` | Canonical public claims boundary | Existing receipt/security behavior |
| `docs/provider-adapters.md` | Existing protocol and registration guide | `adapters/base.py`, `registry.py`, `mock.py` |
| `docs/scenario-packs.md` | Existing example-directory contribution contract | `examples/<scenario>/` |
| `CONTRIBUTING.md` | Contribution and validation path | Existing toolchain and new demo commands |

Planning and evidence files: `CURRENT_REPO_MAP.md`, `BASELINE_TEST_REPORT.md`, and `IMPLEMENTATION_MAPPING.md`.

## Receipt compatibility

The existing required fields, schema version, canonicalization, hash, Ed25519 signature, verifier, committed receipts and conformance vectors remain unchanged. The generated demo receipt adds backward-compatible optional signed metadata: offline mode, original task hash, presentation-only token estimates, local-only estimate, per-provider disclosed estimates, final-output/assessment hashes and verification metadata. Existing receipts continue to verify.

## Final validation

- `python -m ruff check .`: PASS
- `python -m pytest -q`: PASS — 50 passed, 0 failed, 0 skipped
- `apl --help`: PASS, exit 0
- `apl demo`: PASS; exactly three primary artifacts generated
- provider isolation source test: PASS
- external socket rejection test: PASS
- `apl inspect apl-out`: PASS
- `apl verify apl-out/receipt.json`: PASS
- `apl break-receipt apl-out/receipt.json`: PASS as a demonstration; original preserved and tampered copy fails canonical verification
- task-file `preview` and `run`: PASS for files inside an existing scenario pack
- independent venv editable install from a repository-external working directory: PASS
- GIF: 960x540, eight frames, 80,106 bytes
- `git diff --check`: PASS

The in-app browser visual inspection could not start because the managed browser runtime lacked required sandbox metadata. This is classified `ENVIRONMENTAL`; HTML structure, escaping, provider-pane isolation, required labels, generated-file shape and interaction source are covered automatically.

## Definition of Done audit

- Existing code audited before implementation: complete.
- Requested capabilities mapped to actual paths: complete.
- One canonical runtime/receipt/verifier/provider abstraction/exposure definition: preserved.
- Mock demo routes through canonical ProviderRegistry: complete.
- Demo uses real receipt signing and verification: complete.
- Existing production workflows: 50-test suite and baseline commands pass.
- Receipt compatibility: preserved with optional signed metadata only.
- Changed existing files documented: complete.
- README matches tested behavior and puts enterprise content near the end: complete.
- Proposed `src/` tree was not imposed: complete.

No commit, push, PR, release, repository initialization, or destructive cleanup was performed.
