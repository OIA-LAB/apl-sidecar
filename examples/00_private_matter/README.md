# 00_private_matter — The cloud gets the task. It does not get the deal.

> One matter file contains the acquisition, the price terms, the board status, and the negotiation posture. The model needs only the drafting task.

## Scenario

An associate at a small corporate law firm advises **Tarnwell Group** — a fictional, exchange-listed regional cold-chain logistics operator — on its proposed acquisition of **Marrowfield Provisions**, a fictional family-owned specialty food distributor.

Internal deal codename:

> **Project Lantern**

The associate wants model help with a routine task:

* tighten a due-diligence request list;
* draft a short cover note to opposing counsel.

The working matter file contains far more than the model needs:

* party identities and the codename mapping;
* negotiation posture and internal approval status;
* price terms and deal red flags.

Together, those details reveal the existence, structure, status, and economics of an unannounced transaction.

Sending them to a third-party model could create three independent risks:

* **privilege waiver**;
* **MNPI mishandling**;
* **breach of the transaction NDA**.

The cloud gets the drafting task.

It does not get the deal.

## What APL recorded

**Authorized outbound content:**
The codename-level drafting request.

**Retained locally:**
The privileged appendix containing identities, deal terms, approval status, negotiation posture, and identified risks.

The exact outbound payload is included in this fixture for inspection.

## Why this demo exists

A script can delete a marked appendix.

This fixture demonstrates the evidence layer around that disclosure decision.

APL:

* checks configured outbound payloads against declared local-only values;
* shows the exact payload authorized for each configured provider path;
* records the applicable policy identifier with each recorded payload;
* cryptographically binds the outbound payload, provider identifier, timestamp, and run metadata;
* allows the resulting receipt to be verified offline;
* detects later modification of the signed record.

The minimum evidence loop is:

> declare the boundary → inspect the model view → check the payload → sign the disclosure record → detect tampering

This fixture intentionally keeps the disclosure boundary simple and human-auditable.

It does not claim that semantic reconstruction is impossible, or that this fixture alone demonstrates automated classification, fragmentation, or host-wide egress control.

## How this demo runs

The fixture contains:

* one complete fictional working matter file;
* the exact outbound payload;
* a signed receipt binding that payload to the recorded run;
* an intentionally modified receipt for negative verification.

The offline path replays the fixture-defined policy without contacting a model provider.

The live path:

```bash
apl run-live
```

shows the exact outbound payload and requires explicit confirmation before anything is sent.

## Verify it yourself

Everything below runs offline, with no API keys or network access.

From the repository root:

```bash
# 1. Run the leak gate.
#
# Confirm that no declared local-only value appears in any configured
# provider payload.
apl mask examples/00_private_matter

# Expected:
# OK -- no local-only value appears in any provider payload.
```

```bash
# 2. Replay the offline demo end to end.
#
# This writes:
#   apl-out/assessment.md
#   apl-out/exposure.html
#   apl-out/receipt.json
#
# The newly generated receipt is self-verified before the command completes.
apl demo \
  --scenario examples/00_private_matter \
  --output apl-out
```

```bash
# 3. Inspect the committed fixture receipt.
#
# Review:
#   - exposure per configured provider
#   - fields retained locally
#   - field and payload fingerprints
#   - policy and run metadata
apl inspect examples/00_private_matter/receipt.json
```

```bash
# 4. Verify the committed fixture receipt against the demo public key.
apl verify \
  examples/00_private_matter/receipt.json \
  --pubkey spec/apl-oss-demo-key-02.pem

# Expected:
# Signature verified. Receipt chain valid.
```

```bash
# 5. Prove that tampering breaks verification.
apl verify examples/00_private_matter/tampered_receipt.example.json

# Expected:
# Verification failed: receipt was modified or signature is invalid.
```

The final command must fail.

## Verification details

`apl verify` recomputes the receipt hash and verifies its Ed25519 signature.

The demonstration public key is included in:

```text
spec/apl-oss-demo-key-02.pem
```

Public-key SHA-256 fingerprint:

```text
eac16bcd46e48d3303c35a713b945454b395f793e12aab623580d48faaf94412
```

Any modification to a signed field causes verification to fail.

Anyone holding the receipt, verifier, and corresponding public key can perform this integrity check offline, without contacting OIA Lab or a model provider.

## What this receipt proves

For the recorded APL run, the receipt proves that:

* the receipt has not been altered since it was signed by the stated APL signing key;
* the recorded outbound payload is cryptographically bound to the receipt;
* the configured provider identifier, timestamp, policy metadata, and run metadata are bound to the same signed record;
* a third party can verify that integrity offline.

## What this receipt does not prove

The receipt does not independently prove:

* the absence of other egress paths on the host machine;
* that the configured provider actually received the payload;
* the real-world identity of the provider;
* the independent accuracy of the host-generated timestamp;
* how the provider processed, stored, retained, or reused the payload;
* that semantic reconstruction is impossible;
* that the selected disclosure boundary was optimal.

APL makes a narrower, testable promise:

> Show what its configured execution path authorized, bind that record cryptographically, and make later alteration detectable.

## Inspect every byte. Then break the receipt.

The complete matter file contains the deal.

The model-facing payload contains the task.

The signed receipt records the difference.

---

All entities, transaction details, commercial terms, and events in this fixture are fictional.

"Local" refers to the runtime boundary demonstrated by APL. The fixture itself is intentionally public test data. Even the fictional price terms are shown redacted, by design.
