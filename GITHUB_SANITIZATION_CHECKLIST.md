# GitHub Sanitization Checklist

Every item must be confirmed before any push of this repository.
This checklist itself ships with the repo as a living gate.

> Status: last full manual pass 2026-07-11 (initial publication), all items
> confirmed. Items enforced by CI carry a (CI) marker -- they are re-checked
> on every test run, not just at publication time.

## Content

- [x] No customer data.
- [x] No private patent data.
- [x] No golden findings.
- [x] No internal patent pack templates.
- [x] No AIP paid workflow templates.
- [x] No internal metrics.
- [x] No unstable metrics (nothing published that cannot be recomputed from the repo).
- [x] No customer names.
- [x] No client prompts.
- [x] No private workflow logic (production decomposition rules stay closed).
- [x] All example content is fictional, synthetic, and marked as such.

## Secrets

- [x] No secret keys of any kind. (CI)
- [x] No vendor API keys (see scan list below). (CI)
- [x] No hidden `.env` files.
- [x] No production keypair; only public verification keys are committed. (CI)
- [x] (CI) Secret scan passes (`python -m pytest tests/ -k hygiene` where applicable).

Secret scan minimum term list:

```
OPENAI_API_KEY
ANTHROPIC_API_KEY
GOOGLE_API_KEY
GEMINI_API_KEY
XAI_API_KEY
OPENROUTER_API_KEY
ZHIPU_API_KEY
AWS_ACCESS_KEY
AWS_SECRET_ACCESS_KEY
CLOUDFLARE_API_TOKEN
VERCEL_TOKEN
SUPABASE_KEY
DATABASE_URL
PRIVATE_KEY
```

(Referring to these names in scanners and docs is fine; committed VALUES are not.)

## Paths and terms

- [x] No private repo paths.
- [x] No internal machine paths (e.g. drive letters, user home dirs).
- [x] (CI) Deprecated-vocabulary gate passes:
      `python -m pytest tests/test_no_deprecated_terms.py -q`
      (the legacy no-single-cloud underscore term must not appear anywhere;
      canonical term is `no_single_provider_saw_full`).

## Network posture

- [x] No real provider default calls; mock/offline is the default everywhere.
- [x] No live vendor is required to run the P0 demo.
- [x] Playground binds loopback only.
