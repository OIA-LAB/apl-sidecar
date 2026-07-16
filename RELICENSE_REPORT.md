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
(pending)

## Phase 4 — Governance docs
(pending)

## Phase 5 — Wording sweep
(pending)

## Phase 6 — Acceptance
(pending)

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

(To be finalized with the full grep in Phase 5.)
