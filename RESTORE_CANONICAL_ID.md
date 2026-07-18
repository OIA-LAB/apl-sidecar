# Restore canonical license identifier (tracking)

**Status: OPEN**

## What
`apl-sidecar`'s `pyproject.toml` declares the runtime license as:

    license = "LicenseRef-FSL-1.1-ALv2"

The canonical identifier is **`FSL-1.1-ALv2`** (Fair Source License 1.1 with an
Apache-2.0 future grant; full text in `LICENSE`). The `LicenseRef-` prefix is a
temporary encoding, not a different license.

## Why (observed at v0.2.0 publish)
Publishing the wheel with the plain `license = "FSL-1.1-ALv2"` was rejected by
the publishing toolchain (`pypa/gh-action-pypi-publish`) at upload time:

    InvalidDistribution: Invalid distribution metadata:
    'FSL-1.1-ALv2' is invalid for 'license-expression'

The wheel emits `Metadata-Version: 2.4` with `License-Expression: FSL-1.1-ALv2`,
and the toolchain validates that expression against an SPDX license list that
does not yet carry the `FSL-1.1-ALv2` identifier (FSL is a Fair Source license,
not an SPDX/OSI one). `LicenseRef-<id>` is SPDX's standard escape hatch for
licenses not on the list and is always accepted. `apl-verifier` is `Apache-2.0`
(on the SPDX list) and was unaffected.

Note: a plain local `twine check` does NOT catch this — the SPDX-list check runs
in the publish path, not in `twine check`. The exact publish-side twine/packaging
versions are recorded in the release's `RELEASE_COMPLETE` record.

## Restore condition
When the publishing action's bundled toolchain recognizes `FSL-1.1-ALv2` in its
SPDX license list, change `pyproject.toml` back to:

    license = "FSL-1.1-ALv2"

and remove the `LicenseRef-` prefix. Then close this item.

## Invariants (unchanged either way)
- `LICENSE` full text is untouched.
- Every source file keeps its `SPDX-License-Identifier: FSL-1.1-ALv2` header.
- The license and the rights granted are exactly FSL-1.1-ALv2; only the
  machine-readable metadata identifier is prefixed.
