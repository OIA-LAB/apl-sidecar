# Masking Levels

APL uses a small ladder to describe masking capability honestly. The level
used is written into every receipt (`masking_level`), so a receipt never
claims more intelligence than was actually applied.

| Level | Name                    | Description                                         | P0 Status            |
| ----- | ----------------------- | --------------------------------------------------- | -------------------- |
| L0    | Deterministic / regex   | Obvious patterns such as fake keys, emails, IDs     | Partial              |
| L1    | Local NER / small model | Names, organizations, locations                     | Roadmap              |
| L2    | Workflow-aware masking  | Task-specific semantic decomposition                | Enterprise / roadmap |
| P0    | Guided curated          | User marks local-only fields; examples are curated  | **Implemented**      |

## What "guided curated" means

- The user (or the example author) decides what is local-only via
  `masking_plan.yaml`.
- Provider payloads are crafted to carry the abstract task, not the secrets.
- APL then does the real, mechanical part: tracks the local-only fields,
  accounts the exposure, signs the receipt, and verifies tampering.

## What P0 does NOT do

P0 does not automatically detect sensitive fields and does not automatically
decompose a task. If a doc or UI string ever implies otherwise, that is a bug —
file an issue citing this document.
