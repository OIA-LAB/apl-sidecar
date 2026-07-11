# Baseline Test Report

Baseline date: 2026-07-12 (Asia/Taipei)
Baseline commit: `3e9456ae318a4894c94cb0363063223cf809594a6`
Branch: `main`

This report captures behavior before Developer-First Launch implementation. `CURRENT_REPO_MAP.md` is the only untracked audit artifact present while these commands ran; no production file had been modified.

## Commands and results

| Command | Result |
| --- | --- |
| `python -m ruff check .` | PASS — all checks passed |
| `python -m pytest -q --basetemp D:\tmp\apl-baseline-pytest -p no:cacheprovider` | ENVIRONMENTAL — 43 passed, one `tmp_path` setup error because the managed sandbox denied creation of the requested temp directory |
| Same pytest command with approved temp-directory access and unique path | PASS — 44 passed in 0.67s |
| `apl --help` | Existing behavior: prints module usage, exits 2; target launch behavior is not implemented |
| `apl preview examples\00_private_idea` | PASS, exit 0 |
| `apl inspect examples\00_private_idea\receipt.json` | PASS, exit 0 |
| `apl verify examples\00_private_idea\receipt.json` | PASS, exit 0; prints signature and chain valid |
| `apl rehydrate examples\00_private_idea` | PASS, exit 0 |
| `apl run-mock examples\00_private_idea` | PASS, exit 0; offline fixture responses and a locally signed ignored receipt |

Skipped tests: 0.
Product-test failures: 0.
Known environment limitation: managed Windows sandbox may deny pytest's temp-directory creation unless a writable temp path is explicitly approved. Classified `ENVIRONMENTAL`.

## Existing CLI behavior

- No arguments or `--help`: prints the usage docstring and exits 2.
- `preview <example_dir>`: displays original character count, local-only fields, the exact two curated provider payloads, per-provider character exposure, maximum exposure, and the no-full-view boolean. It performs no provider call.
- `mask <example_dir>`: runs the documented exact-substring leak check.
- `run-mock <example_dir>`: loads deterministic fixture answers, generates and signs the canonical receipt, and writes ignored `receipt.local.json` beside the example.
- `rehydrate <example_dir>`: displays provider answers, fields reintroduced locally, and the curated local final output.
- `inspect <receipt.json>`: displays receipt metadata, provider exposure, local-only fingerprints, provenance, and integrity identifiers.
- `verify <receipt.json>`: verifies the canonical receipt offline using the reference verifier.
- `playground`: serves the static app on loopback.
- `proxy`: serves offline mock OpenAI-compatible endpoints on `127.0.0.1:8793`.

## Existing sample output facts

For `examples/00_private_idea`:

- Original: 1,774 normalized characters.
- Provider A payload: 553 characters, 31.2% character exposure.
- Provider B payload: 485 characters, 27.3% character exposure.
- Seven named fields remain local and only their fingerprints enter the receipt.
- The committed receipt verifies successfully.
- Rehydration states that it is produced locally from fixture answers and local-only context.
- `run-mock` explicitly prints that no network call was made.

## Baseline regression rule

After implementation, the same commands must pass. `apl --help` is expected to become a successful intentional extension. Any other behavior change must be classified as `INTENTIONAL`, `UNINTENTIONAL`, `PRE_EXISTING`, or `ENVIRONMENTAL`; unintentional regression blocks completion.
## Post-implementation regression result

Final result on 2026-07-12: Ruff passed; 50 tests passed with 0 failures and 0 skips; baseline preview, inspect, verify, rehydrate and run-mock behavior remained operational. `apl --help` intentionally changed from exit 2 to exit 0. New demo, run, output-directory inspect and break-receipt behavior passed. The earlier temp-directory denial remains classified `ENVIRONMENTAL`; approved writable temp execution passed.
