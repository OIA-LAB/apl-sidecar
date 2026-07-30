# APL Task Egress Receipt Standard (v0.1.0-draft)

A receipt is a signed, chainable, tamper-evident record of **what left the
local machine for one AI task**: which payload went to which provider, what
fraction of the original input each provider received, and which sensitive
fields never left at all.

The receipt proves what was sent. It does not prove what a provider retained.

## 1. Canonical fields

```json
{
  "run_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
  "task_type": "private_idea",
  "policy_id": "apl-oss-demo-policy",
  "provider_events": [
    {
      "provider_id": "mock_provider_a",
      "payload_sha256": "<64 lower-hex>",
      "payload_chars": 214,
      "response_sha256": "<64 lower-hex or null>",
      "event_type": "mock_response"
    }
  ],
  "local_only_hashes": [
    { "field": "product_name", "sha256": "<64 lower-hex>" }
  ],
  "single_provider_exposure": [
    { "provider_id": "mock_provider_a", "exposure_ratio": 0.21 }
  ],
  "max_single_provider_exposure": 0.25,
  "no_single_provider_saw_full": true,
  "prev_receipt_hash": null,
  "receipt_hash": "<64 lower-hex>",
  "signature": { "alg": "Ed25519", "value": "<base64>" },
  "signing_key_id": "demo-key-01",
  "masking_level": "guided_curated_p0",
  "provenance": {
    "apl_sidecar_version": "0.1.0-draft",
    "receipt_schema_version": "0.1.0-draft",
    "policy_version": "0.1.0-draft",
    "example_id": "00_private_idea",
    "created_at": "2026-01-01T00:00:00Z"
  }
}
```

Field notes:

- `run_id` — ULID (Crockford base32, 26 chars).
- `task_type` — lowercase snake_case identifier (pattern-constrained, not an
  enum), so scenario packs can introduce new task types without a schema
  change. P0 ships `private_idea` and `private_code_context`.
- `provider_events[].payload_sha256` — sha256 (lower-hex) over the UTF-8 bytes
  of the payload text after CRLF→LF normalization.
- `local_only_hashes` — fingerprints of fields that never left the machine.
- Live runs (`apl run-live`) may add signature-covered optional event fields:
  `endpoint_host`, `model`, `response_chars`, `response_truncated`,
  `completion` (`complete` | `truncated` | `unknown` — the tri-state source of
  truth; `response_truncated` is its legacy boolean projection), and
  `usage` (provider-reported token counts, whitelisted and int-coerced;
  provider-asserted, not verified). Mock fixtures omit them.
  Content is NOT in the receipt; only the hash is.
- `single_provider_exposure[].exposure_ratio` —
  `characters_sent_to_provider / characters_in_original_input`. This is a
  cumulative disclosure ratio, NOT a fraction: a payload that restates or
  expands shared context can legitimately exceed `1.0`, and per-trust-domain
  aggregates are sums of seat ratios, so they exceed `1.0` whenever fragments
  overlap. Capping at 1 would under-report — receipts must never do that.
- `no_single_provider_saw_full` — true iff no provider payload equals the
  full original input (canonical term; the legacy no-single-cloud underscore vocabulary
  must not appear anywhere -- CI-gated).
- `prev_receipt_hash` — previous receipt's `receipt_hash` (hex) or `null` for
  the first receipt of a chain.
- `masking_level` — see docs/masking_levels.md; P0 emits `guided_curated_p0`.

## 2. Canonicalization

`receipt_hash` = sha256, lower-hex, over the canonical serialization of the
receipt object with the `receipt_hash` and `signature` members removed.

This canonical serialization is a **specific, named algorithm — `apl-json-v1`
— NOT RFC 8785 / JCS.** A second implementer who reads the phrase "canonical
JSON" and reaches for an RFC 8785 library will compute a *different* byte
string (and therefore a different hash) for the same object. The rule is
pinned exactly here so that never happens silently:

`apl-json-v1` is defined as:

```python
json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
           allow_nan=False).encode("utf-8")
```

- keys sorted at every level by Python string comparison, i.e. by Unicode
  **code point** (this differs from JCS, which sorts by UTF-16 code unit; the
  two orders diverge for supplementary-plane / astral characters, U+10000 and
  above — current receipts use fixed ASCII field names, so this case does not
  arise in practice, but the rule is code-point ordering, not JCS ordering);
- no insignificant whitespace;
- non-ASCII characters encoded as UTF-8 (not `\u` escapes);
- **all numbers must be finite** — `NaN`, `Infinity`, `-Infinity` (bare JSON
  tokens accepted by CPython's `json.loads` as an extension) and numeric
  literals that overflow to a non-finite value when parsed (e.g. `1e400`)
  are rejected at both parse time (`load_receipt_json`) and serialization time
  (`allow_nan=False`). This matches RFC 8785, which forbids non-finite numbers,
  and ensures every consistency check of the form `abs(claimed - recomputed) >
  tol` is meaningful (all comparisons with NaN are False, so a NaN claimed
  value silently passes any such check);
- numbers are serialized by CPython's `json.dumps` shortest round-trip `repr`.
  This means **exponent notation is permitted where CPython emits it** (for
  example `round(1/1e6, 6)` serializes as `1e-06`, and large whole-number
  floats as `1e+16`); the value round-trips exactly. P0 emits exposure ratios
  rounded to at most 6 decimal places, so the values that actually appear are
  in a range where this is well defined. (An earlier revision of this document
  said numbers are written "without exponent notation"; that was a spec-vs-
  implementation contradiction — the pinned one-liner above does emit exponent
  form for some in-range values — and has been corrected to match the
  implementation. This is a documentation correction only: no receipt bytes and
  no `receipt_hash` change.)

**Relationship to RFC 8785 / JCS (honest limit).** We do **not** claim
`apl-json-v1` is byte-identical to RFC 8785 for float-free bodies. It diverges
in at least two independent ways: (1) number/float serialization (`1e-06` vs
`0.000001`) and (2) object-key ordering (code point vs UTF-16 code unit) for
astral characters. A stock RFC-8785 verifier is therefore not interchangeable
with this rule.

The finite-number restriction (`allow_nan=False`) aligns with RFC 8785 on that
one point: both reject `NaN`, `Infinity`, `-Infinity`, and overflowing exponent
values such as `1e400`. Agreement on the finite-number rule for the *current*
finite, ASCII-key corpus does not establish general byte identity between
`apl-json-v1` and RFC 8785 — the float-serialization and astral-key divergences
above still apply.

**Versioning / migration boundary.** `apl-json-v1` is the only canonicalization
used by the receipts this document describes. Any future RFC 8785 (or other)
profile MUST be introduced under a **new canonicalization identifier**, never
substituted in place: an in-place change would alter existing receipt hashes
and invalidate already-signed receipts. Because there are two divergence
classes, we make no claim that such a migration would be cheap or
hash-preserving.

Because the hash covers the whole body, **any** modified byte — including
inside `provenance` or `provider_events` — changes `receipt_hash` and breaks
verification. Extra fields are tolerated by the schema reader but are covered
by the hash, so they cannot be silently added or removed either.

## 3. Signature

```
signed_message = UTF-8 bytes of the lower-hex receipt_hash string (64 ASCII chars)
signature.value = base64( Ed25519_sign(private_key, signed_message) )
```

Verification recomputes the canonical hash, checks it equals `receipt_hash`,
then verifies the Ed25519 signature with the public key identified by
`signing_key_id`.

Private keys are never committed. Conformance vectors ship with a **public**
verification key only (`spec/apl-oss-demo-key.pem`; keys are resolved by
`signing_key_id` as `keys/<id>.pem` then `spec/<id>.pem`).

## 4. Chain rule

Receipt N+1 must carry `prev_receipt_hash == receipt_hash of receipt N`.
A verifier walks the chain in order; the first mismatch (or any per-receipt
verification failure) breaks the chain at that index.

## 5. Conformance vectors

`spec/conformance_vectors/valid_chain/` — two receipts forming a valid chain;
both must verify, and the chain must verify.

`spec/conformance_vectors/tamper_vectors/` — five receipts that MUST fail:

| Vector                             | Mutation / finding                              |
| ---------------------------------- | ----------------------------------------------- |
| `tamper_payload_changed.json`      | a `provider_events[].payload_sha256` byte       |
| `tamper_provider_changed.json`     | a `provider_events[].provider_id` value         |
| `tamper_prev_hash_changed.json`    | `prev_receipt_hash`                             |
| `tamper_signature_removed.json`    | `signature` member removed                      |
| `tamper_nonfinite_exposure.json`   | `max_single_provider_exposure: NaN` (non-finite number) |

A conforming implementation accepts both valid vectors and rejects all five
tamper vectors. `tests/test_tamper_vectors.py` enforces this in CI.

## 6. v0.2 additive fields (N-way / live runs)

Receipts produced by `apl run-live` carry `receipt_schema_version`
"0.2.0-draft" and ADD (never change) fields:

- per event: `seat_id`, `provider_kind`, `trust_domain`, `endpoint_host`,
  `model`, `response_chars`, `response_truncated`, `usage`;
- top level: `max_single_seat_exposure`, `trust_domain_exposure[]`
  (`{trust_domain, exposure_ratio, seat_ids}`),
  `max_single_trust_domain_exposure`,
  `no_single_trust_domain_received_all_fragments`.

Semantics: exposure is accounted per seat AND aggregated per trust domain
(vendor hosts collapse to the vendor; other hosts group with the port
stripped -- a port is not an isolation boundary). The legacy
`max_single_provider_exposure` equals the trust-domain maximum, never the
per-seat one. Verifiers MUST recompute the aggregation from the signed
per-seat data when these fields are present and fail on mismatch;
receipts without them (v0.1) remain valid. See docs/fragmentation.md.

## 7. Versioning


`provenance.receipt_schema_version` follows this document. Breaking changes
bump the minor version while in draft (0.1 → 0.2) and are recorded here.

---

*This document is part of the APL Sidecar specification layer and is licensed
under [CC BY 4.0](spec/LICENSE). See [spec/README.md](spec/README.md).*
