# Changelog

## 0.2.1

Demo: replace the 00 fixture scenario with a legal privileged-matter example
(M&A due diligence); regenerate demo receipts and mock outputs. Rename
examples/00_private_idea -> examples/00_private_matter.

apl-verifier unchanged; 0.2.0 remains current.

## 0.2.0

Layered relicensing. The runtime moves to Fair Source (FSL-1.1-ALv2); the
verifier is split into its own permanently Apache-2.0 package (`apl-verifier`);
the specification is CC BY 4.0. v0.1.0 remains MIT — its rights are unchanged.
See [LICENSING.md](LICENSING.md) for the full layer table and FAQ.

PyPI metadata note: the runtime `license` field is published as
`LicenseRef-FSL-1.1-ALv2`. The license itself is unchanged (FSL-1.1-ALv2, full
text in [LICENSE](LICENSE)); the `LicenseRef-` prefix is a temporary encoding
because the current publishing toolchain's SPDX license list does not yet carry
the `FSL-1.1-ALv2` identifier. Tracked in
[RESTORE_CANONICAL_ID.md](RESTORE_CANONICAL_ID.md).

## 0.1.0

Initial release (MIT): local exposure control and signed receipts for sensitive
AI tasks.
