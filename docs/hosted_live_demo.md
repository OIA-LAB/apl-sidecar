# Hosted Live Demo Relay (P1 design)

P1 provides a hosted demo where users experience real AI output **without
bringing an API key**. This is not a free API. It is an **APL Demo Relay**:
an operator-controlled backend holding provider credentials, with rate
limits, quota controls, abuse prevention, and mock fallback.

## Flow

```
Browser UI
  -> APL Demo Backend
  -> Rate Limit / Abuse Guard
  -> Masking Workflow
  -> Provider Payload Preview
  -> Provider Pool
  -> Response
  -> Local-Style Rehydrate
  -> Signed Receipt
  -> Verify / Inspect
```

## User experience

```
Open hosted playground
  -> choose Private Idea or Private Code Context
  -> enter or edit fictional demo input
  -> see local-only fields
  -> see provider payload preview
  -> click Run Live Demo
  -> receive model output
  -> see local-style rehydrated answer
  -> see signed receipt
  -> tamper receipt and verify failure
```

## Mandatory warning (shown before input)

> Hosted demo is for testing the APL experience. Do not paste real secrets.
> For real sensitive content, run APL Sidecar locally or use APL Enterprise
> Gateway.

## Provider pool candidates

| Provider                  | Suggested Role                              |
| ------------------------- | ------------------------------------------- |
| OpenRouter                | Multi-model free / low-cost pool            |
| Google AI Studio / Gemini | Mainstream model experience                 |
| Cloudflare Workers AI     | Edge / lightweight fallback                 |
| Vercel AI Gateway         | Multi-model gateway / credit-based demo     |
| Groq / Cerebras           | Fast inference fallback, later              |
| OpenAI / Claude / xAI     | BYOK or paid-demo mode, not initial default |

## Hard rules

- no provider API key committed;
- no provider API key exposed to the browser;
- no unlimited arbitrary chatbot endpoint;
- no claim that the hosted demo protects real secrets;
- no raw input storage by default;
- no default use for real sensitive content;
- fixed workflows only (`private_matter`, `private_code_context`);
- rate limited; input length limited; daily cost capped;
- mock fallback when quota is exhausted;
- provider pool configurable from the backend;
- a provider can be disabled without a frontend change.

## Rate and cost controls (recommended defaults)

| Control            | Suggested Value                             |
| ------------------ | ------------------------------------------- |
| Per-IP daily limit | 3–5 live runs                               |
| Per-session limit  | 3 live runs                                 |
| Input length       | 2,000–4,000 characters                      |
| Allowed scenarios  | `private_matter`, `private_code_context` only |
| Arbitrary chat     | Disabled                                    |
| Fallback           | Mock response                               |
| CAPTCHA            | P1.1 or later                               |
| Daily cost cap     | Configurable                                |
| Logging            | Operational metadata only                   |

## Modes

| Mode              | Description                                                  |
| ----------------- | ------------------------------------------------------------ |
| `hosted-mock`     | Website demo using mock outputs only                         |
| `hosted-live`     | Limited live model relay                                     |
| `hosted-fallback` | Auto fallback to mock when provider quota/cost limit reached |

## Status

P1 is a design in this repo. A reference relay prototype (provider pool
config, rate limiting, cost cap, mock fallback — runnable locally, no
deployment) may ship under `relay/` as a non-default component.
