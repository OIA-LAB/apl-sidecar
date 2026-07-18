# Contributing to APL Sidecar

APL Sidecar welcomes focused changes that preserve its canonical receipt, verifier, provider abstraction, local stitch boundary, and exposure definition.

Before submitting a change:

```bash
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest -q
apl demo
apl break-receipt apl-out/receipt.json
```

Keep demo data fictional and offline. Do not add credentials, telemetry, silent network fallback, duplicate receipt formats, or unqualified privacy guarantees. New provider adapters and scenario packs should follow the guides under `docs/` and include tests.

## Contributor License Agreement

Code contributions require a signed individual CLA ([CLA.md](CLA.md)) before
they can be merged. Until the CLA is signed, I will discuss a code PR in its
Issue but will not merge it. This keeps the layered licensing in
[LICENSING.md](LICENSING.md) coherent — including the automatic Apache-2.0
conversion of each runtime release two years after its release date.

If you have not signed the CLA, please do not paste code intended for inclusion
in an Issue; describe it or use pseudocode instead. Code posted in an Issue by an
unsigned contributor will not be adopted; the maintainer follows a clean-room
discipline (does not read, take, or reuse it) and reserves the right to
independently reimplement.

CLA signatures are recorded with an independent time anchor (a CLA signing bot,
or an RFC-3161 / OpenTimestamps trusted timestamp) so the signing identity and
time are evidenced independently, not by a self-recomputable hash alone.

Documentation-only fixes (typos, broken links, clarifications) are exempt and
can be merged without a CLA.

