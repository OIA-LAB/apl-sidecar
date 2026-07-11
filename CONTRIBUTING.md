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
