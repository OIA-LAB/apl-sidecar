# Security Policy

## What this project is

APL Sidecar P0 is a **local, offline playground** for AI task exposure control.
By default it makes zero network calls, requires no API keys, and stores
nothing outside the repo directory.

## What this project is NOT

- It is not an anonymity tool.
- It does not provide cryptographic secrecy of task content.
- It does not control or attest what any AI provider retains.
- The hosted demo (P1) is for experiencing the flow only — never paste real
  secrets into it.

See [docs/not_claims.md](docs/not_claims.md) for the full claim boundary.

## Reporting a vulnerability

Open a GitHub security advisory or a private issue. Include reproduction steps.
Do not include real secrets or personal data in reports.

Areas we care about most:

1. Receipt verification bypass (a tampered receipt that verifies as valid).
2. Signature or hash canonicalization ambiguity.
3. The playground server binding to a non-loopback interface.
4. Anything that causes the mock/offline default to make a network call.

## Key handling

- No private keys are committed to this repo (CI-checked).
- Demo signing keys are generated locally into a gitignored directory.
- The committed conformance vectors carry only a **public** verification key.
