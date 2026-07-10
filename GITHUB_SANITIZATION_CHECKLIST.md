# GitHub Sanitization Checklist

Every item must be confirmed before any push of this repository.
This checklist itself ships with the repo as a living gate.

## Content

- [ ] No customer data.
- [ ] No private patent data.
- [ ] No golden findings.
- [ ] No internal patent pack templates.
- [ ] No AIP paid workflow templates.
- [ ] No internal metrics.
- [ ] No unstable metrics (nothing published that cannot be recomputed from the repo).
- [ ] No customer names.
- [ ] No client prompts.
- [ ] No private workflow logic (production decomposition rules stay closed).
- [ ] All example content is fictional, synthetic, and marked as such.

## Secrets

- [ ] No secret keys of any kind.
- [ ] No vendor API keys (see scan list below).
- [ ] No hidden `.env` files.
- [ ] No production keypair; only public verification keys are committed.
- [ ] Secret scan passes (`python -m pytest tests/ -k hygiene` where applicable).

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

- [ ] No private repo paths.
- [ ] No internal machine paths (e.g. drive letters, user home dirs).
- [ ] Deprecated-vocabulary gate passes:
      `python -m pytest tests/test_no_deprecated_terms.py -q`
      (the legacy no-single-cloud underscore term must not appear anywhere;
      canonical term is `no_single_provider_saw_full`).

## Network posture

- [ ] No real provider default calls; mock/offline is the default everywhere.
- [ ] No live vendor is required to run the P0 demo.
- [ ] Playground binds loopback only.
