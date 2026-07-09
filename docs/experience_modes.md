# Experience Modes

| Mode          | Description                                                    | API key | Network | Default      |
| ------------- | -------------------------------------------------------------- | ------- | ------- | ------------ |
| `mock`        | Offline fixture-based provider responses                       | No      | No      | **Yes**      |
| `hosted-live` | OIA-controlled backend relay using a provider pool             | No      | Yes     | Website only |
| `byok`        | User brings their own API key                                  | Yes     | Yes     | No           |
| `enterprise`  | Production deployment with policy, routing, audit, governance  | Depends | Depends | No           |

## P0 default: mock / offline only

The public repo defaults to mock/offline:

- no API key;
- no login;
- no network;
- no live vendor call;
- no hidden provider dependency.

Allowed adapters in the public repo: `mock_provider_a`, `mock_provider_b`,
`local_stub`. No live vendor (OpenAI, Anthropic, Google, Zhipu, xAI,
OpenRouter, Cloudflare, Vercel, …) is used by default or bound as a
dependency. Live providers may be listed only as P1 / BYOK / hosted-demo
directions.

## hosted-live (P1)

See [hosted_live_demo.md](hosted_live_demo.md). It is a relay controlled by
the project operator — not a public free API — with rate limits, cost caps,
and mock fallback.

## byok

Bring-your-own-key mode is a direction, not a P0 feature: the adapter
interface is designed so that a live adapter drops in where the mock adapters
sit today, reading its key from your environment only.

## enterprise

Production policy enforcement, provider governance, deployment controls and
audit evidence live in APL Enterprise Gateway — outside this repo.
See [enterprise_gateway.md](enterprise_gateway.md).
