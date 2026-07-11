# Scenario Packs

A scenario pack follows the existing `examples/<scenario>/` boundary. It can be added without changing the runtime.

Required files:

- `input.original.example.txt` — fictional original task;
- `masking_plan.yaml` — task type, local-only field names, preserved signals, and routing explanation;
- `local_only.json` — fictional values retained locally;
- `provider_a_payload.txt` and `provider_b_payload.txt` — distinct controlled disclosures;
- `mock_answer_a.txt` and `mock_answer_b.txt` — deterministic offline responses;
- `final_rehydrated_answer.txt` — explicitly local, fixture-backed final artifact;
- `receipt.json` and tamper fixture when the scenario is committed as a conformance example.

Scenario data must be synthetic. Medical, legal, financial, patent, customer, or real-company data is not accepted for the v0.1 demo. Provider payloads must pass the local-only exact-substring gate and both mock providers must use the canonical adapter registry.
