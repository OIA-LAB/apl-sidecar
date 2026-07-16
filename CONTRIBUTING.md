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

Documentation-only fixes (typos, broken links, clarifications) are exempt and
can be merged without a CLA.

