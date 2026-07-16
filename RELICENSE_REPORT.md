# RELICENSE_REPORT — APL Sidecar v0.2.0 Layered Relicensing

Branch: `relicense/v0.2.0` (based on `main` @ c0049f1). Executed 2026-07-16.
Work order (single source of truth): `private-data/WORKORDER_RELICENSE_v0.2.0_FINAL_20260716.md`.

This report is the accumulating evidence log. Every number cites its source.

---

## Phase 0 — Preflight & isolation

### Git anchors (verified, not re-derived)
| Item | Value | Source |
| --- | --- | --- |
| HEAD | `c0049f1d096874ebd8006a4ad764221a0e2df5ef` | `git rev-parse HEAD` |
| v0.1.0^{commit} | `7ea0ac69ccc3774211141d2c705408542429b53d` | `git rev-parse v0.1.0^{commit}` |
| branch | `relicense/v0.2.0` | `git branch --show-current` |

The v0.1.0 tag commit above is the invariant re-checked in Phase 6.

### Split-local isolation
Not applicable. No split-local residue exists: `cli/commands/split_local.py`
and `tests/test_split_local.py` are absent, and `git ls-files | grep split_local`
returns nothing. Nothing to quarantine or `git checkout --`.

### Author / rights-holder audit
`git shortlog -sne --all`:
- `OIA-LAB <oia-lab@users.noreply.github.com>` — 25 commits
- `Y.C Chang <udo.chang@w-flux.com>` — 1 commit

`git log --format='%an <%ae>' | sort -u` yields the same two identities. Both
are the sole proprietor (YC). No third-party code author. Relicensing may
proceed. See OPEN QUESTIONS for the licensor-spelling note.

### Baseline
- Tests: `python -m pytest -q` → **126 passed** (baseline, pre-change).
- Lint: `python -m ruff check .` → **All checks passed!**

### Hygiene fixes applied in Phase 0
- `.venv/`, `venv/`, `_licfetch/` added to `.gitignore` (the `_licfetch/`
  scratch dir with license originals + write-smoke must never be committed).
- `tests/test_no_deprecated_terms.py`: hygiene gates now anchor to
  `git ls-files --cached --others --exclude-standard` (`_git_file_set()`)
  instead of a raw `rglob`, so `.venv/` and build artifacts are excluded
  exactly as git excludes them. `test_no_private_keys_committed` rewritten to
  scan that file set and permanently enabled — no `--deselect` hereafter.

---

## Phase 1 — Verifier extraction (Apache-2.0)

New package `packages/apl-verifier/` (Apache-2.0, version 0.2.0):
- `src/apl_verifier/`: `trust.py` (single normalize_host/trust_domain rule),
  `receipt.py` (schema constants, canonical bytes, hash, shape/trust-domain
  checks, `load_public_key` requiring an explicit path, `verify_receipt`/
  `verify_chain`), `plugins.py` (interface-only planner/provider Protocols,
  zero implementation), `cli.py` (`apl-verify` console script; `--pubkey`
  REQUIRED, no repo-relative key/spec search), `__init__.py` (public API).
- `LICENSE` = byte-exact Apache-2.0 (sha256 `cfc7749b…`), `NOTICE`, `README.md`
  (states permanent Apache-2.0), `pyproject.toml` (license = "Apache-2.0",
  no `License ::` classifiers, console script `apl-verify`, dep: cryptography).

Dependency direction (runtime → apl-verifier, never reverse):
- `cli/commands/_verifier_boot.py` (new bridge): makes `apl_verifier`
  importable from a source checkout, and keeps KEY-LOCATION policy runtime-side
  (`resolve_pubkey_path`: user key dir then packaged spec key), passing an
  explicit path into the pure verifier.
- `cli/commands/_common.py`: `normalize_host`/`trust_domain`/
  `VENDOR_TRUST_DOMAINS` now imported from `apl_verifier` — the duplicated copy
  was DELETED (single source; verified by `test_verifier_host_rule_is_single_source`).
- `_signing.py`, `verify.py`, `run_live.py` rewired to the package/bridge (no
  more `sys.path.insert(REPO/"verifier") + import apl_verify`).
- `cli/commands/_resources.py`: added `spec_key_path()` (path to packaged demo
  PUBLIC key, wheel-safe).

Deprecated shim: `verifier/apl_verify.py` re-exports the package API, keeps the
old auto key-resolution for legacy callers, emits `DeprecationWarning`, notes
v0.3 removal. `verifier/README.md` updated to point at the package.

Isolation tests:
- (a) static: `packages/apl-verifier/tests/test_isolation.py` — AST scan fails
  if any `apl_verifier` source imports a runtime module (cli/adapters/relay/
  app/verifier/apl_verify/examples/spec). PASS.
- (b) standalone: `packages/apl-verifier/tests/test_verify_standalone.py` —
  synthetic Apache-licensed fixture (generated at runtime, NO CC BY vectors
  bundled): valid receipt verifies, tampered rejected, missing/bad key rejected.
  PASS. (The full clean-venv wheel install is the Phase 6 hard gate.)

Runtime tests repointed to the new architecture (no logic mocked, no
`--deselect`): auto-resolution tests → `cli.commands._verifier_boot`; pure
checks → `apl_verifier`. `test_signing_key_id_traversal_rejected` now asserts
BOTH layers reject a traversal id (bridge before FS, and pure `load_public_key`
with an explicit key). `test_packaged_public_key_fallback` monkeypatches the
user key dir empty and confirms the bridge still resolves the packaged spec key.

Evidence: `python -m pytest -q` → **132 passed** (126 baseline + 5 package
tests + 1 net new single-source test); `-W error::DeprecationWarning` also 132
passed (no runtime path hits the shim). `ruff check . packages/apl-verifier` →
All checks passed. Shim manually confirmed to emit DeprecationWarning and still
verify a committed receipt.

## Phase 2 — Spec layer (CC BY 4.0)

- `spec/LICENSE` = byte-exact CC BY 4.0 legalcode (sha256 `9ba9550a…`).
- `spec/README.md` (new): directory-level CC BY notice + index. States the
  notice covers every file in `spec/` (JSON/YAML vectors and schemas included),
  and that vectors carry NO inline footer/`license` field because canonical
  bytes must stay immutable. Declares `conformance_vectors/` the single source
  of truth that the verifier tests reference from a checkout.
- `RECEIPT_STANDARD.md` (spec profile narrative, Markdown): CC BY footer
  appended (footer allowed on Markdown; the JSON/YAML were deliberately left
  untouched). Kept at repo root — see OPEN QUESTIONS #2 — because README and
  code doc-comments anchor to that path; physically moving it was judged a
  risky, non-load-bearing change not spelled out by the work order.
- The already-present `spec/{receipt.schema.json, policy_manifest.schema.json,
  demo_policy_manifest.json, conformance_vectors/**, apl-oss-demo-key.pem}` are
  the field definitions + vectors the work order lists; no bytes changed.

Evidence: `pytest -q` → 132 passed (RECEIPT_STANDARD footer broke nothing; no
canonical vector bytes changed). `ruff` green.

## Phase 3 — Runtime relicense (FSL-1.1-ALv2)

- Root `LICENSE` = FSL-1.1-ALv2 template with the TWO allowed substitutions
  only (`${year}`→`2026`, `${licensor name}`→`Yu-Chia Chang (張育嘉)`),
  generated by `_licfetch/_subst_fsl.py` (CJK-safe, file I/O not stdin). Post-
  substitution assert: no `${` placeholder remains. sha256 `139df728…`.
- `LICENSES/` (new) holds all three full texts:
  - `FSL-1.1-ALv2.md` sha256 `139df728…` (== root LICENSE)
  - `Apache-2.0.txt` sha256 `cfc7749b…` (byte-exact original)
  - `CC-BY-4.0.txt` sha256 `9ba9550a…` (byte-exact original)
- Root `pyproject.toml`: `requires = ["setuptools>=77.0.3"]`; `version =
  "0.2.0"`; `license = "FSL-1.1-ALv2"`; `license-files = ["LICENSE",
  "LICENSES/*"]`; added `apl-verifier>=0.2.0,<0.3.0` to dependencies. No
  `License ::` classifier existed in either package (nothing to remove).
- SPDX headers: `_licfetch/_add_spdx.py` prepended
  `# SPDX-License-Identifier: FSL-1.1-ALv2` to all 55 tracked runtime `.py`
  (no shebang/coding-cookie collisions). `packages/apl-verifier/**` already
  carried `# SPDX-License-Identifier: Apache-2.0`. One file
  (`tests/test_openai_proxy.py`) had a UTF-8 BOM that landed mid-file after the
  prepend; the stray BOM was stripped (byte-level fix, no logic touched).
- New gate `tests/test_spdx_headers.py`: every tracked `.py` must carry the
  SPDX line for its layer (runtime FSL, verifier Apache-2.0). Always on.

`python -m build` (PEP 517, isolated) — BOTH succeed:
- `apl_verifier-0.2.0-py3-none-any.whl` + sdist. Wheel dist-info license =
  Apache-2.0, LICENSE+NOTICE bundled, `apl-verify` entry point present.
- `apl_sidecar-0.2.0-py3-none-any.whl` + sdist. Wheel METADATA:
  `License-Expression: FSL-1.1-ALv2`; `License-File:` LICENSE + all 3 under
  LICENSES/; `Requires-Dist: apl-verifier<0.3.0,>=0.2.0`; NO `License ::`
  classifier. (Artifacts built into gitignored `_licfetch/_dist/`.)

Evidence: `pytest -q` → 133 passed. `ruff check . packages/apl-verifier` green.

## Phase 4 — Governance docs

- `LICENSING.md` (new): layer table (spec CC BY 4.0; verifier/SDK Apache-2.0
  permanent; runtime v0.2+ FSL-1.1-ALv2, each version → Apache-2.0 at 2yr;
  v0.1.0 MIT historical; planner/evaluator = repo-external commercial) + FAQ
  (why FSL, why verifier permanently open, v0.1.0 users unaffected). First
  person singular, factual, no marketing. No forbidden terms.
- `CONTRIBUTING.md` (updated): added CLA section — code PRs need a signed CLA
  before merge; discussed in the Issue until then; doc-only typos exempt.
- `CLA.md` (new): individual CLA adapted from Apache ICLA v2.2. Header line
  `<!-- LAWYER-REVIEW REQUIRED — not effective until reviewed -->`. Outbound
  license clause (§4) explicitly covers current FSL distribution AND "the
  automatic conversion of each distributed version of the runtime to the Apache
  License, Version 2.0 upon the second anniversary". (Legal-clause terms in
  CLA.md are a rule-2 exception, so the ICLA's patent-grant language is allowed
  here and only here.)
- `CHANGELOG.md` (new): 0.2.0 entry (two-to-three lines on the relicensing,
  links to LICENSING.md) + a 0.1.0 baseline line. No forbidden terms.

Evidence: `pytest -q` → 133 passed. `ruff` green. Forbidden-term scan of
LICENSING.md/CONTRIBUTING.md/CHANGELOG.md = 0 hits.

## Phase 5 — Wording sweep

MIT / open-source sweep (git-tracked, license files + report excluded):

| Location | Referent | Action |
| --- | --- | --- |
| `README.md:5` badge `license: MIT` | runtime (current) | → FSL-1.1-ALv2 badge |
| `README.md` "open-source Sidecar" (Enterprise Gateway §) | runtime v0.2 | → "Fair Source (FSL-1.1-ALv2) Sidecar" |
| `README.md` License § "MIT — see LICENSE" | runtime license | → layered summary (FSL runtime / Apache verifier / CC BY spec; v0.1.0 MIT unchanged) |
| `docs/enterprise_gateway.md:3` "open-source entry point" | runtime | → "Fair Source (FSL-1.1-ALv2) entry point" |
| `CHANGELOG.md`, `LICENSING.md` "MIT" | **v0.1.0 historical fact** | KEPT (v0.1.0 was MIT; stating history is required, work-order rule 5) |
| `README.md:270` "v0.1.0 release remains MIT" | v0.1.0 historical | KEPT (same reason) |
| `examples/00_private_idea/input.original.example.txt:20`, `.../local_only.json:6` "open-source launch" | **fictional scenario GTM** of a made-up startup, not this repo | KEPT (fictional demo content; changing it would falsify the scenario) |

README top now carries a 3-line layered-license summary + LICENSING.md link
(no marketing sentence added).

### Rule 2 — forbidden-term grep = 0 (with exceptions)
Word-boundary scan of all tracked text files, excluding basename `LICENSE*`,
`LICENSES/**`, `CLA.md`, `RELICENSE_REPORT.md`, and this gate's own source:

- **0** newly-introduced forbidden terms.
- The only `patent` hits remaining are the two ruling-#3 pre-existing ones:
  `docs/enterprise_gateway.md:10` and `docs/scenario-packs.md:15` (present at
  v0.1.0, not added by this work). Both allow-listed by the gate.
- `scripts/smoke_installed_wheel.py:60` "PYTHONPATH" is a substring false
  positive (contains "NPA"); a word-boundary match excludes it.

Enforced permanently by `tests/test_relicensing_terms.py` (no --deselect).

## Phase 6 — Acceptance

### R1-executor independent re-verification (2026-07-16)
Two defects were caught during independent re-verification and fixed before the
acceptance commit (not mocks, not `--deselect` — the real safety properties are
preserved and now correctly cover the frozen conformance key):

1. **`.gitignore` swallowed the frozen conformance public key.** The rule
   `*.pem` + `!spec/*.pem` un-ignores only the immediate `spec/` dir, so
   `spec/conformance/v0.1.0/apl-oss-demo-key.pem` was still ignored and would
   never have committed — silently breaking the Phase-6 hard gate. Added
   `!spec/conformance/**/*.pem`. Verified the key is a PUBLIC key
   (`BEGIN PUBLIC KEY`, Ed25519), safe to ship.
2. **`test_no_private_keys_committed` location check was too narrow.** It
   asserted every shipped `.pem` sits exactly in `REPO/spec`; the frozen
   conformance key lives in `spec/conformance/v0.1.0/`. Widened the location
   assertion to "under `spec/`" (`spec_dir in f.parents`) while keeping the
   actual security check (`"PRIVATE" not in text`) fully intact.

All Phase-6 evidence below was re-run independently after these fixes:
`pytest -q` → 136 passed; `ruff` green; both wheels build; offline wheelhouse
(verifier→runtime) installs; clean-venv `apl demo`/`verify`/`break-receipt`
behave as baseline; the v0.1.0 conformance pair verifies+rejects
(`pytest -k v010` → 2 passed, not skipped).

Checklist (work-order Phase 6), each with evidence:

- [x] **Full test suite green** (incl. restored private-key test, SPDX-header
      test, verifier isolation ×2): `python -m pytest -q` → **136 passed**
      (130 runtime/tests + 6 apl-verifier package tests). No `--deselect`.
- [x] **lint green**: `ruff check . packages/apl-verifier` → All checks passed.
- [x] **forbidden grep = 0** (with exception list): word-boundary scan → only
      the two ruling-#3 pre-existing `patent` docs remain; gate
      `tests/test_relicensing_terms.py` enforces it.
- [x] **verifier version 0.2.0; runtime depends apl-verifier>=0.2.0,<0.3.0**:
      installed metadata — `apl-verifier` License-Expression Apache-2.0,
      version 0.2.0; `apl-sidecar` Requires-Dist `apl-verifier<0.3.0,>=0.2.0`.
- [x] **build two wheels; offline wheelhouse install (verifier then runtime);
      smoke passes**: both wheels built via `python -m build`; clean venv
      installed `apl_verifier-0.2.0` then `apl_sidecar-0.2.0` from the local
      wheelhouse; both resolved in order.
- [x] **clean venv: runtime apl demo / verify / break-receipt vs baseline**
      (run from a temp dir OUTSIDE the checkout → exercises the installed
      wheel): `apl demo` → receipt generated + "Signature verified. Receipt
      chain valid." (exit 0); `apl verify` → same message (exit 0);
      `apl break-receipt` → tamper detected, "Verification failed…" (exit 0).
      Console script `apl-verify`: valid+`--pubkey` exit 0, missing `--pubkey`
      usage exit 2, tamper exit 1 — matches baseline behaviour.
- [x] **[HARD GATE] apl-verifier 0.2.0 verifies a REAL v0.1.0 receipt and
      rejects its tamper; pair frozen as spec/conformance/v0.1.0/**: vectors
      extracted verbatim from the v0.1.0 tag (`receipt.json` sha256
      `4d5c5fb2…`, `tampered_receipt.json` sha256 `e5c9d01d…`,
      `apl-oss-demo-key.pem` sha256 `a97d01d1…`, byte-identical to the current
      spec key). Real receipt VERIFIED; tamper REJECTED (`receipt_hash
      mismatch`). Enforced by
      `packages/apl-verifier/tests/test_v010_conformance.py`.
- [x] **v0.1.0^{commit} unchanged**: `git rev-parse v0.1.0^{commit}` =
      `7ea0ac69ccc3774211141d2c705408542429b53d` — identical to Phase 0.
- [x] **three license source URLs + sha256 + two substitutions**: recorded in
      "License source provenance" above; FSL substitutions `${year}`→2026,
      `${licensor name}`→`Yu-Chia Chang (張育嘉)`.
- [x] **diffstat, Phase 0 isolation list, OPEN QUESTIONS**: below.

### Diffstat (vs base c0049f1, all six phase commits)
`git diff --stat c0049f1 HEAD`: **85 files changed, ~3079 insertions,
~487 deletions**. Six commits, exact work-order names:
- `b1e21ec` chore: quarantine local-only experiments
- `dcac643` refactor: extract independent verifier package
- `3868d36` docs: separate specification licensing
- `5b45e94` chore: apply layered licensing metadata
- `d6e2c79` docs: add contribution and licensing governance
- `3f74ff6` chore: sweep licensing wording and add relicensing term gate
- (Phase 6 acceptance commit follows this report update.)

### Phase 0 isolation list
No split-local residue existed (isolation = not applicable); nothing was
quarantined or reverted. Author audit: OIA-LAB (25) + Y.C Chang (1), both YC.

### Scratch cleanup note
`_licfetch/` (license originals, substitution/SPDX scripts, build wheelhouse,
smoke venv, write-smoke) is gitignored and never committed. `build/` and
`dist/` are gitignored. Nothing scratch entered the repo.

---

## License source provenance (Phase 3/6 detail)
Originals fetched into `_licfetch/` (untracked, gitignored). sha256 re-verified
before use, all match the work-order preflight:

| File | Bytes | sha256 | Source URL |
| --- | --- | --- | --- |
| FSL-1.1-ALv2.template.md | 3751 | `36b6082235c0a2105174927fc57cc6ae9c41f45a08af2bdcaee18a8dace56177` | https://raw.githubusercontent.com/getsentry/fsl.software/main/FSL-1.1-ALv2.template.md |
| Apache-2.0.txt | 11358 | `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30` | https://www.apache.org/licenses/LICENSE-2.0.txt |
| CC-BY-4.0.txt | 18657 | `9ba9550ad48438d0836ddab3da480b3b69ffa0aac7b7878b5a0039e7ab429411` | https://creativecommons.org/licenses/by/4.0/legalcode.txt |

Substitution values (FSL template only): `${year}` → `2026`;
`${licensor name}` → `Yu-Chia Chang (張育嘉)`.

---

## OPEN QUESTIONS
2. **RECEIPT_STANDARD.md physical location.** The work order says spec/
   "collects" the receipt profile document. RECEIPT_STANDARD.md is the profile
   narrative but lives at repo root and is anchored by `README.md` and code
   doc-comments (`cli/commands/run_live.py`, `_common.py`). It was licensed
   CC BY 4.0 in place (footer + `spec/README.md` index entry) rather than
   physically moved, to avoid an out-of-scope, link-breaking move. If you want
   it physically under `spec/`, that's a follow-up (update the 3 anchors).
1. **Licensor spelling vs git author.** Ruling #2 (2026-07-16) fixes the
   licensor name as `Yu-Chia Chang (張育嘉)`. The sole git author identity is
   `Y.C Chang <udo.chang@w-flux.com>` (+ the `OIA-LAB` GitHub noreply account).
   Per ruling #2 this difference is recorded here and does **not** block; the
   FSL `${licensor name}` substitution uses the ruling spelling. If the PPA
   applicant field differs again, PPA wins (work-order 代換值 note) — not
   verified here (private-data is read-only, no PPA inspected).

---

## Exception lists

### Rule 2 — forbidden-term (`patent`/`patent-pending`/`PPA`/`NPA`/`™`/`(TM)`) exceptions
Pre-existing hits retained per ruling #3 (既存非新增, not added by this work):
- `docs/enterprise_gateway.md:10` — "patent and invention disclosure workflows"
  (existed at v0.1.0; enterprise scenario prose, not a claim). Retained.
- `docs/scenario-packs.md:15` — "…legal, financial, patent, customer…" (a list
  of data types that scenario data must NOT be; existed at v0.1.0). Retained.

Finalized in Phase 5: word-boundary grep confirms these are the ONLY two
`patent` hits outside license/CLA/report; zero new forbidden terms introduced.
The `scripts/smoke_installed_wheel.py` "PYTHONPATH" substring is a false
positive (not the token NPA). Gate: `tests/test_relicensing_terms.py`.
