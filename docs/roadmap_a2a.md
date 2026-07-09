# Roadmap: APL for A2A

APL for A2A extends task exposure receipts from human-to-model workflows to
agent-to-agent workflows, where multiple agents may gradually infer the
user's full intent through coordination.

**P0 does not support A2A.** This document is a direction, not a feature.

## Why A2A changes the problem

With a single model call, exposure is a per-provider question. In a
multi-agent task graph, no single hop may see the full context — yet the
*coalition* of agents, across turns, can reconstruct it. Exposure control
then needs to reason about accumulated context per agent and per coalition,
not per request.

## Candidate scenarios (directional, no P0 claims)

| A2A Scenario                          | Risk                                   | Future APL control point       |
| ------------------------------------- | -------------------------------------- | ------------------------------ |
| Procurement agent vs supplier agent   | Reserve price inferred                 | Per-round quote exposure receipt |
| Recruiting agent vs candidate agent   | Salary range and preferences leak      | Salary boundary control          |
| Legal agent vs opposing-party agent   | Settlement floor leaks                 | Negotiation intent boundary      |
| Investment agent vs research agent    | Positions and trade intent leak        | Portfolio local-only             |
| Multi-agent collaboration in-company  | Cross-department data gets stitched    | Agent exposure graph             |

## What would carry over from P0

The receipt standard: signed, chainable, tamper-evident records of who saw
what and how much. A2A adds the graph dimension; the evidence layer stays.
