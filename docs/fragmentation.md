# N-Way Fragmentation (2–5 seats)

APL can split a task across 2 to 5 seats. This page is the honest version
of what that buys you, what it does not, and how the receipt accounts for
it. The hard rule first:

> **Seats are not providers, and providers are not trust domains.**
> Three seats that all resolve to the same vendor mean that vendor
> received ALL of those fragments.

## What fragmentation measurably does

Splitting lowers the **per-seat disclosure share** — the fraction of your
characters any single seat receives. That number is measured from the
generated payloads and signed into the receipt. It is a disclosure-volume
measurement, not a privacy score.

Idealized reference (equal, non-overlapping fragments, each seat on an
**independent trust domain**): per-seat volume sits near `1/N`. Measured
values are always scenario-specific and usually higher, because curated
payloads restate enough context to stay answerable.

| N | idealized 1/N | measured max seat share |
|---|---------------|-------------------------|
| 2 | 0.500 | 0.312 — `examples/00_private_idea`, fragment plan v1 |
| 3 | 0.333 | 0.319 — `examples/02_market_entry_three_way`, fragment plan v1 |

Both measured values come from the bundled fictional scenarios, computed
over CRLF-normalized character counts of the shipped payload files versus
the original input, with no shared-fragment overlap. Reproduce them:

```bash
apl preview examples/00_private_idea
apl preview examples/02_market_entry_three_way
```

These numbers are **not** a general privacy-improvement rate and **not** a
reconstruction-risk reduction. They change with every fragment plan.

## What fragmentation does NOT guarantee

- **Reconstruction risk is a different measurement.** It usually drops as
  disclosure share drops, but it is not guaranteed to — a ten-character
  fragment can still reveal the entire intent. APL measures disclosure and
  signs it; it does not score semantic reconstruction.
- **More fragments = more parties see something.** Every extra seat widens
  the set of providers holding a piece of your task, and with it the
  collusion surface. Fewer, better-chosen fragments often beat many.
- **Same trust domain = exposure aggregates.** If several fragments go to
  seats that resolve to one trust domain, that domain's exposure is the
  SUM of those fragments. The preflight prints a structural warning:

  ```
  WARNING: 3 seats resolve to the same trust domain "openai".
  Fragment count does not reduce exposure to that provider.
  ```

- **Answer quality is an expected trade-off.** Each seat answers with less
  context, and the final synthesis happens locally, on you. No quantified
  quality claim is made here; treat quality as something to check per
  task. (The bundled examples show tasks that split well — separable
  workstreams. Tasks that are one indivisible question do not.)

## Trust-domain rule (exactly as implemented)

`trust_domain(endpoint_host)`:

1. lowercase the host, strip the port — **a port is not an isolation
   boundary**; two ports on one host are the same domain;
2. known vendor API hosts collapse to the vendor label
   (`api.anthropic.com` → `anthropic`, `api.openai.com` → `openai`);
3. anything else aggregates by its host (e.g. `127.0.0.1`, your vLLM box).

Two seats with the same kind but genuinely different endpoints (say, the
official OpenAI API and a local OpenAI-compatible server) are different
trust domains under this rule — the receipt signs `endpoint_host` per
event, so the grouping is auditable and recomputable.

## What the receipt signs (v0.2, additive)

Per event: `seat_id`, `provider_kind`, `trust_domain`, `endpoint_host`,
`payload_sha256`, `payload_chars`. Top level:

- `max_single_seat_exposure` — the biggest single fragment;
- `trust_domain_exposure[]` + `max_single_trust_domain_exposure` — the
  aggregation that actually matters;
- `no_single_trust_domain_received_all_fragments` — false when one domain
  got everything, no matter how many seats it was dressed up as;
- the legacy `max_single_provider_exposure` carries the **trust-domain**
  maximum, never the per-seat one.

The verifier recomputes the aggregation from the signed per-seat data and
fails the receipt on any mismatch. v0.1 receipts (without these fields)
remain valid — the fields are additive.

## Supported range: 2–5, enforced

`N < 2` or `N > 5` exits with code 2. Beyond five seats the marginal gain
in idealized share is tiny (1/5 → 1/6 saves ≈ 0.03) while manual fragment
quality and the collusion surface both get worse. This is a hard limit in
this version, not advice.

## Declaring fragments

```yaml
# masking_plan.yaml
fragments:
  - id: pricing
    payload: provider_a_payload.txt
    mock_answer: mock_answer_a.txt
  - id: channel
    payload: provider_b_payload.txt
    mock_answer: mock_answer_b.txt
  - id: risk
    payload: provider_c_payload.txt
    mock_answer: mock_answer_c.txt
```

Examples without a `fragments:` key keep the original two-seat behaviour,
byte-identical. Live runs name every seat explicitly:

```bash
apl run-live examples/02_market_entry_three_way \
    --seat pricing=anthropic --seat channel=openai --seat risk=openai
```

Unknown ids, duplicates, missing or extra seats: exit 2, zero transport.
