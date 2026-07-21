# Changelog

## 0.2.2

Packaging fix: the wheel/sdist now ship `spec/apl-oss-demo-key-02.pem` (and the
JSON schemas + spec README/LICENSE), so the flagship `00_private_matter` demo
receipt verifies from a clean `pip install` — previously the bundled key was
omitted and `apl verify` failed with "no public key found for
signing_key_id='apl-oss-demo-key-02'". The `spec` package-data allowlist was
replaced with a glob (`*.pem`, `*.json`, `*.md`, `LICENSE`).

Measurement-floor smoke: the installed-wheel smoke now verifies **every**
shipped example receipt from an empty neutral cwd + empty `APL_KEY_DIR` (no
`--pubkey`), and asserts `resources.files('spec')` resolves under
site-packages — catching the cwd-shadow false-green that hid the 0.2.1 bug. The
false-green `test_packaged_public_key_fallback` unit test was rewritten to build
and install the wheel and run that same check from a temp cwd. The release
publish gate (unchanged in shape) blocks on this smoke.

Claim narrowing (no new assets shipped): clarified that the CC-BY spec's
conformance vectors live in the source repo, not the wheel (the wheel bundles
runtime + schemas + demo keys); documented that `02_market_entry_three_way`
ships no static receipt (run-mock/run-live generates it).

Docs: replaced the stale "install from this repository" line with
`pip install apl-sidecar` / `pipx install apl-sidecar` as the primary path and
clarified that the scenario READMEs' `examples/`-relative verify steps are the
source-checkout path.

apl-verifier unchanged; 0.2.0 remains current.

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
