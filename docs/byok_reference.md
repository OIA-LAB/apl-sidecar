# BYOK Reference Implementation

`apl run-live` is the reference implementation of the real-provider path
required by the security model: real providers, your keys, network on,
**off by default**, no silent fallback from mock to live. It exists
so that the receipt pipeline can be exercised against live endpoints without
waiting for the enterprise gateway.

## What it does

```
apl run-live examples/00_private_idea --a anthropic --b openai --yes
```

1. **Leak gate.** The exact rule `apl mask` enforces (shared implementation:
   `cli/commands/_common.py::leak_findings`). A masking plan that fails the
   gate is never transmitted — exit 1, zero network calls.
2. **Pre-flight consent.** Prints each seat's destination host, model,
   payload size, and exposure ratio, then requires you to type `send`
   (or pass `--yes`). Non-interactive sessions without `--yes` refuse.
3. **Transmission.** One user message per provider containing only the
   approved payload. No system prompt, no metadata, temperature 0.
4. **Live receipt.** Ed25519-signed with your local demo key,
   `event_type: "live_response"`, plus signature-covered optional fields per
   event: `endpoint_host`, `model`, `response_chars`, `response_truncated`,
   and provider-reported `usage` token counts. The receipt is verified before
   the command reports success. A partial run (one provider failed) still
   writes a signed receipt: what was disclosed was disclosed. A response the
   provider cut off at its length limit is marked `response_truncated: true`
   and warned about — a partial answer never masquerades as complete.
5. **Local rehydration.** Provider answers and local-only context are
   combined into `combined_answer.local.md` on your machine only.

## Seats and configuration (environment-only)

Keys never appear on the command line or in files this repo reads.

| Seat kind   | Required                            | Optional |
| ----------- | ----------------------------------- | -------- |
| `anthropic` | `ANTHROPIC_API_KEY`                 | `APL_ANTHROPIC_MODEL[_<FRAGMENT_ID>]`, `APL_ANTHROPIC_BASE_URL`, `APL_ANTHROPIC_MAX_TOKENS` |
| `openai`    | `APL_OPENAI_MODEL[_<FRAGMENT_ID>]`; `OPENAI_API_KEY` unless the endpoint is loopback | `APL_OPENAI_BASE_URL[_<FRAGMENT_ID>]` |

The `openai` seat speaks to any OpenAI-compatible `/v1/chat/completions`
endpoint. That one code path covers a hosted vendor, a **local model server**
(vLLM, Ollama, llama.cpp) on loopback — the customer-controlled local seat —
and the repo's own offline mock proxy.

## Chaining runs into one audit trail

Every receipt carries `prev_receipt_hash`. Link consecutive runs with
`--chain` and verify the whole trail in one command:

```
apl run-live examples/00_private_idea --yes
apl run-live examples/01_private_code_context --yes \
    --output apl-live-out-2 --chain apl-live-out/receipt.live.json
apl verify apl-live-out/receipt.live.json apl-live-out-2/receipt.live.json
```

The chain gate is fail-close and runs before any socket opens: if the
previous receipt does not verify, nothing is transmitted.

## Offline end-to-end rehearsal of the live path

The entire live pipeline can be rehearsed with zero external network by
pointing both seats at the bundled proxy:

```
apl proxy --port 8793   # terminal 1 — loopback-only mock proxy

# terminal 2
export APL_OPENAI_BASE_URL=http://127.0.0.1:8793/v1
export APL_OPENAI_MODEL_MOCK_PROVIDER_A=apl-mock-a
export APL_OPENAI_MODEL_B=apl-mock-b
apl run-live examples/00_private_idea --a openai --b openai --yes
apl verify apl-live-out/receipt.live.json
```

This makes a real HTTP round trip on loopback and produces a genuine
`live_response` receipt, without any key and without leaving the machine.

## What this is not

This reference does not claim provider non-retention, network or account
anonymity, or automatic semantic decomposition — the boundaries in
[not_claims.md](not_claims.md) apply unchanged. Masking remains user-guided
(`guided_curated_p0`); the leak gate is exact-substring only and does not
detect paraphrased leakage. Key handling is best-effort hygiene (environment
input, scrubbed error paths, never written to receipts or artifacts), not a
secrets manager. Exposure accounting remains character-based.
