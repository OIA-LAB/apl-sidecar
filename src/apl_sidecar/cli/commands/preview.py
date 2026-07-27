# SPDX-License-Identifier: FSL-1.1-ALv2
"""apl preview -- show local-only fields, disclosures, estimates, and residual risk."""
from __future__ import annotations
from . import _common as c


def run(example_dir: str) -> int:
    paths = c.example_paths(example_dir)
    local_only = c.load_local_only(paths)
    view = c.exposure_view(paths)
    original = c.read_text(paths["original"])
    print("=" * 64)
    print(f"APL PREVIEW -- {paths['dir'].name}")
    print("=" * 64)
    print(f"\nOriginal input: {view['original_chars']} characters "
          f"(~{c.estimated_tokens(original)} tokens; {paths['original'].name})")
    print("\n-- LOCAL-ONLY (never leaves this machine) " + "-" * 20)
    for field, value in local_only.items():
        shown = value if isinstance(value, str) else str(value)
        print(f"  {field}: {shown[:70]}{'...' if len(shown) > 70 else ''}")
    for provider, payload_path in paths["payloads"].items():
        info = view["providers"][provider]
        payload = c.read_text(payload_path)
        print(f"\n-- {provider.upper()} SEES ({info['exposure_ratio']:.1%} "
              f"of original, {info['chars']} chars, ~{c.estimated_tokens(payload)} tokens) "
              + "-" * 8)
        print(payload.strip())
    print("\n-- ESTIMATED EXPOSURE " + "-" * 40)
    for provider, info in view["providers"].items():
        print(f"  {provider}: {info['exposure_ratio']:.1%}")
    print(f"  max_single_provider_exposure: {view['max_single_provider_exposure']:.1%}")
    print(f"  no_single_provider_saw_full: {view['no_single_provider_saw_full']}")
    print("\nResidual disclosure risk: payloads preserve category, audience, and task intent.")
    print("Warning: token counts are estimates; receipt exposure remains character based.")
    print("Note: P0 uses user-guided masking and curated provider payloads.")
    return 0
