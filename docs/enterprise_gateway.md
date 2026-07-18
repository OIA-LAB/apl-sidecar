# APL Enterprise Gateway

APL Sidecar (this repo) is the Fair Source (FSL-1.1-ALv2) entry point: it teaches the
language of AI task exposure control — local-only, provider payload,
exposure accounting, signed receipt, tamper-fail verification.

Enterprise and vertical workflows are handled through **APL Enterprise
Gateway**, which is not part of this repository. It covers:

- patent and invention disclosure workflows;
- supplier negotiation and procurement analysis;
- financial and board-level document workflows;
- medical research and sensitive case summarization;
- legal, compliance, and internal governance workflows.

Enterprise-grade requirements the public repo deliberately does not include:

- production policy enforcement (registered workflow packs, reject-at-load
  policy validation, run-time fail-close gates);
- provider governance (allowlists, data-residency rules, egress control);
- deployment controls (sidecar/gateway topologies, private connectivity);
- audit evidence at scale (append-only stores, chain verification services,
  SIEM/compliance export);
- workflow-specific evidence packs and production decomposition rules.

The public repo does not include enterprise routing logic, production
decomposition rules, private workflow templates, or customer data — and it
never will. That boundary is what keeps this repo safe to run, read, and
extend.

Contact: open a GitHub issue with the `enterprise` label.
