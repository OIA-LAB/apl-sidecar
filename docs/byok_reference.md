# BYOK Reference Implementation

`apl run-live` is an optional reference implementation of the real-provider
path. Offline `apl demo` remains the default. Live mode never starts silently:
you must choose `run-live`, inspect the preflight, and either type `send` or
pass `--yes` as explicit network consent.

Always preview the scenario first:

```powershell
apl preview examples/00_private_idea
```

## Environment-only credentials

Use environment variables, never command-line key arguments or committed files.
These placeholders are not real credentials:

```powershell
$env:OPENAI_API_KEY="<your-openai-key>"
$env:APL_OPENAI_MODEL="<your-openai-model>"

$env:ANTHROPIC_API_KEY="<your-anthropic-key>"
$env:APL_ANTHROPIC_MODEL="<your-anthropic-model>"  # optional
```

OpenAI-compatible loopback endpoints do not require `OPENAI_API_KEY`. Hosted
OpenAI-compatible endpoints do. Anthropic always requires
`ANTHROPIC_API_KEY`.

## Two-seat live example

The bundled two-way scenario uses fragment IDs `mock_provider_a` and
`mock_provider_b`:

```powershell
apl preview examples/00_private_idea
apl run-live examples/00_private_idea `
  --seat mock_provider_a=anthropic `
  --seat mock_provider_b=openai `
  --yes
```

Without `--yes`, the CLI prints each destination, payload size, seat exposure,
and trust-domain aggregate, then requires typed consent.

## Three-seat live example

The market-entry scenario declares `pricing`, `channel`, and `risk`:

```powershell
apl preview examples/02_market_entry_three_way
apl run-live examples/02_market_entry_three_way `
  --seat pricing=anthropic `
  --seat channel=openai `
  --seat risk=openai `
  --yes
```

The supported fragment range is 2–5. Three or more fragments require explicit
`--seat FRAGMENT_ID=PROVIDER_KIND` mapping for every fragment.

## Same-provider trust-domain warning

Seat names do not create provider independence. Sending all three fragments to
OpenAI resolves them to one trust domain and prints a warning before transport:

```powershell
apl run-live examples/02_market_entry_three_way `
  --seat pricing=openai `
  --seat channel=openai `
  --seat risk=openai `
  --yes
```

The receipt aggregates all three disclosures under the same trust domain.

## What run-live does

1. **Leak gate.** Uses the same exact-substring rule as `apl mask`. A failure
   exits before transport.
2. **Preflight and consent.** Shows every named seat and trust-domain aggregate
   before any request.
3. **Transmission.** Sends one user message per approved fragment, with no
   system prompt and temperature 0.
4. **Signed receipt.** Records the payload hash, endpoint host, model, response
   hash, truncation state, and provider-reported usage when available.
5. **Local rehydration.** Writes `combined_answer.local.md` locally.

A partial transport failure still leaves signed disclosure evidence; it cannot
fabricate a successful provider response.

## Chaining runs

```powershell
apl run-live examples/00_private_idea `
  --seat mock_provider_a=anthropic `
  --seat mock_provider_b=openai `
  --output apl-live-out-1 `
  --yes

apl run-live examples/01_private_code_context `
  --seat mock_provider_a=anthropic `
  --seat mock_provider_b=openai `
  --output apl-live-out-2 `
  --chain apl-live-out-1/receipt.live.json `
  --yes

apl verify apl-live-out-1/receipt.live.json apl-live-out-2/receipt.live.json
```

An invalid prior receipt fails before transport.

## Loopback-only rehearsal

This exercises the actual HTTP path without an API key or external network.
Start the bundled loopback proxy:

```powershell
apl proxy --port 8793
```

In another terminal:

```powershell
$env:APL_OPENAI_BASE_URL_MOCK_PROVIDER_A="http://127.0.0.1:8793/v1"
$env:APL_OPENAI_BASE_URL_MOCK_PROVIDER_B="http://127.0.0.1:8793/v1"
$env:APL_OPENAI_MODEL_MOCK_PROVIDER_A="apl-mock-a"
$env:APL_OPENAI_MODEL_MOCK_PROVIDER_B="apl-mock-b"

apl preview examples/00_private_idea
apl run-live examples/00_private_idea `
  --seat mock_provider_a=openai `
  --seat mock_provider_b=openai `
  --yes
apl verify apl-live-out/receipt.live.json
```

Both seats normalize to trust domain `127.0.0.1`, so the CLI correctly warns
that fragment count does not create provider isolation.

## Boundaries

This reference does not claim provider non-retention, anonymity, automatic
semantic decomposition, or production readiness. Masking remains user-guided
and the leak gate is exact-substring only. Keys are environment inputs scrubbed
from known error paths, not managed by a secrets manager. Exposure accounting
remains character-based and is not a reconstruction-risk score.