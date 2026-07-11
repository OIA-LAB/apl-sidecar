# Current Repository Map

Audit date: 2026-07-12 (Asia/Taipei)

This document records the pre-implementation state for the Developer-First Launch work order. The existing repository is authoritative; the conceptual tree in the work order is not a migration target.

## A. Repository identity

- Repository: `D:\apl-sidecar`
- Branch: `main`
- Commit: `3e9456ae318a4894c94cb0363063223cf809594a6`
- Working tree at audit start: clean (no tracked modifications or untracked files)
- Local history: three commits ahead of `origin/main`:
  - `6e05a72 Package project and add cross-platform CI`
  - `3ed06e9 Add offline provider adapters and OpenAI-compatible proxy`
  - `3e9456a Align Private Mode messaging and canonical schema IDs`
- Remote: `origin https://github.com/OIA-LAB/apl-sidecar.git` for fetch and push
- Untracked files: none
- Ignored runtime files: `.ruff_cache/`, Python `__pycache__/`, `apl_sidecar.egg-info/`, local receipts, and `keys/`
- Active runtime: CPython 3.12.10 at `C:\Users\udoch\AppData\Local\Programs\Python\Python312\python.exe`
- Installed package: editable `apl-sidecar 0.1.0` from this repository
- Package definition: `pyproject.toml`, setuptools, Python >=3.11
- Console launch: `apl = cli.apl:main`
- Source-compatible launch: `python cli/apl.py ...`

The audit found no `AGENTS.md` in the repository.

## B. Existing architecture

| Capability | Canonical or current implementation |
| --- | --- |
| CLI entry points | `cli/apl.py`; installed entry in `pyproject.toml` |
| Demo/sample workflows | `examples/00_private_idea/`, `examples/01_private_code_context/`; commands in `cli/commands/` |
| Disclosure/decomposition | Curated payloads plus `masking_plan.yaml`; path and accounting helpers in `cli/commands/_common.py` |
| Provider adapters | New protocol/registry in `adapters/base.py`, `adapters/registry.py`, `adapters/mock.py`; legacy fixture responders in `adapters/mock_provider_a/` and `mock_provider_b/` |
| Provider routing | Explicit offline registry in `adapters/mock.py`; separate prototype gate in `relay/relay_server.py` |
| Local execution | Fixture-backed mock responses; `adapters/local_stub/provider.py` for explicit local routing |
| Local stitch | Curated `final_rehydrated_answer.txt`, displayed by `cli/commands/rehydrate.py`; no reusable stitch function yet |
| Receipt generation | `cli/commands/run_mock.py` builds the canonical receipt body; `cli/commands/_signing.py` signs it |
| Receipt verification | Canonical verifier in `verifier/apl_verify.py`; CLI wrapper in `cli/commands/verify.py` |
| Tamper detection | Canonical hash/signature verification plus fixtures in `spec/conformance_vectors/tamper_vectors/` and example tampered receipts |
| Exposure measurement | Canonical v0.1 definition is normalized character count in `cli/commands/_common.py` and `docs/exposure_model.md` |
| Reconstruction/risk assessment | No executable assessment; boundary text exists in docs. This is missing for the requested demo |
| OpenAI-compatible proxy | `relay/openai_proxy.py`, loopback-only offline mock; CLI command `apl proxy` |
| HTML/UI output | Static local playground in `app/local_playground/`; it reads bundled scenarios but does not generate per-run `exposure.html` |
| Scenario fixtures | Two canonical examples under `examples/`; each contains original, local-only data, provider payloads/answers, masking plan, final output, and signed receipt |
| Tests | 44 tests across receipt/schema/tamper/relay/public hygiene/adapters/proxy |
| Documentation | Root README, receipt standard, security notes, product boundaries and enterprise docs under `docs/` |

### Canonical implementation constraints

- Receipt schema: `spec/receipt.schema.json`; do not replace it with the illustrative work-order JSON.
- Receipt hash/signature verification: `verifier/apl_verify.py`; all new tamper behavior must call this verifier.
- Receipt generation/signing: `cli/commands/run_mock.py` and `_signing.py`; extend rather than duplicate.
- Provider abstraction: `adapters/base.py` plus explicit `ProviderRegistry`; the older fixture modules should be adapted behind this interface, not expanded as a second abstraction.
- Exposure measurement: normalized character ratios are the published canonical metric. Token estimates may be added as presentation-only estimates and must not silently redefine the receipt metric.
- Local stitch: current artifact and display behavior must remain compatible; a thin reusable orchestration function may be extracted without changing existing output.

## C. Reuse classification

| Requested capability | Classification | Audit finding |
| --- | --- | --- |
| `apl demo` | MISSING | Existing commands cover individual stages but no one-command artifact-producing loop exists |
| `apl preview` | EXISTS_NEEDS_EXTENSION | Accepts example directories, not arbitrary task files; lacks token estimate and explicit residual-risk output |
| `apl run` | MISSING | `run-mock` exists and must be reused/wrapped |
| `apl inspect` | EXISTS_NEEDS_EXTENSION | Receipt-only terminal view; does not inspect output directories or generated HTML/assessment |
| `apl verify` | EXISTS_AND_REUSE | Canonical offline Ed25519 verification already exists |
| `apl break-receipt` | MISSING | Tamper fixtures exist, but no safe copy-and-verify command |
| Provider A/B views | EXISTS_NEEDS_EXTENSION | Static playground has views; generated per-run isolated artifact is missing |
| Local stitch | EXISTS_NEEDS_REFACTOR | Behavior exists as curated artifact plus display command, but orchestration needs a reusable thin boundary |
| Canonical receipt | EXISTS_AND_REUSE | Signed receipt schema, generation, vectors, and verifier are established |
| Exposure HTML | MISSING | Static playground is not a generated run artifact |
| Assessment | MISSING | No executable reconstruction assessment or `assessment.md` |
| Exposure metrics | EXISTS_NEEDS_EXTENSION | Character accounting exists; requested display also needs clearly labeled token estimates and local-retained estimate |
| Offline mock adapters | EXISTS_NEEDS_REFACTOR | Protocol registry exists, but `run_mock.py` still directly imports legacy fixture modules |
| OpenAI-compatible example | EXISTS_NEEDS_EXTENSION | Proxy exists; README example and tested model naming need alignment |
| Scenario packs | EXISTS_NEEDS_EXTENSION | Directory fixtures exist without a documented contribution contract |
| Public-claim tests | EXISTS_NEEDS_EXTENSION | Deprecated vocabulary and secret gates exist; requested prohibited-claim qualification is not covered |
| README launch sequence | EXISTS_NEEDS_REFACTOR | Current README is accurate but does not follow the developer-first demo sequence |
| Demo GIF | MISSING | No `assets/apl-demo.gif` exists |
| `apl --help` | MISSING | No argparse/help surface; empty invocation prints module usage and exits 2 |

## D. Conflict report

1. The work order says “create a new public GitHub repository,” while the addendum and actual state require preserving this existing repository. The addendum wins; no repository initialization or structural migration will occur.
2. The proposed `src/apl_sidecar/` tree conflicts with the established top-level `cli/`, `adapters/`, `verifier/`, `relay/`, `examples/`, and `app/` layout. Existing paths will be retained.
3. The illustrative receipt fields conflict with the canonical signed receipt schema. The demo will expose the real existing receipt and may only add backward-compatible optional metadata if justified.
4. Requested token counts differ from the canonical character-based exposure definition. Token counts will be labeled estimates in presentation artifacts; receipt exposure semantics remain unchanged.
5. Requested `apl preview <task-file>` conflicts with the existing `apl preview <example_dir>` contract. Compatibility requires directory support to remain; any file support must be an extension.
6. Requested `apl run` overlaps `run-mock`; it should orchestrate or alias the existing canonical path, not introduce another runtime.
7. Existing `run_mock.py` bypasses the newly added `ProviderRegistry` and uses legacy fixture modules directly. The launch loop must converge on the canonical adapter interface while preserving old command output and tests.
8. Existing local stitch is a curated output file, not computed composition. The demo may present this deterministic local artifact, but must state that it is fixture-backed and must not imply model-generated local synthesis.
9. Current README foregrounds limitations and architecture before a one-command demo. The work order explicitly supersedes this presentation order, while factual limitations must remain accessible later in the document.
10. Current static playground and requested generated `exposure.html` overlap in presentation purpose. The generated artifact should reuse the existing visual vocabulary/data, not become a second runtime.
11. Existing OpenAI proxy models are `apl-mock-a` and `apl-mock-b` on port 8793; the illustrative example uses `apl-demo` on 8787. Documentation must match tested behavior unless compatibility aliases are intentionally added.
12. `pipx install apl-sidecar` is a target public-install experience but is not proof that a package is currently published. README must distinguish repository installation until publication is authorized.
13. The main work order requests a GIF. Producing it must be based on actual CLI behavior; no fabricated verification result is allowed.
14. The current branch is `main`, clean, and already contains three local unpushed commits. Creating the recommended feature branch now would change the locally approved commit arrangement; implementation will remain on the current branch unless separately directed.

## Audit conclusion

The repository already has credible canonical receipt, verification, exposure accounting, mock fixtures, provider abstraction, proxy, and UI building blocks. The smallest compliant implementation is a thin orchestration and presentation layer around those paths, plus CLI extensions and launch documentation. A parallel runtime, receipt, verifier, or exposure formula is neither necessary nor permitted.
