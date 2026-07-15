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
(pending)

## Phase 2 — Spec layer (CC BY 4.0)
(pending)

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
