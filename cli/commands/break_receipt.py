# SPDX-License-Identifier: FSL-1.1-ALv2
"""Create a one-field tampered receipt copy and prove canonical verification fails."""
from __future__ import annotations
import json
from pathlib import Path
from . import verify


def run(receipt_path: str) -> int:
    source = Path(receipt_path)
    if not source.is_file():
        print(f"receipt not found: {source}")
        return 1
    try:
        receipt = json.loads(source.read_text(encoding="utf-8"))
        old_value = receipt["provider_events"][0]["payload_sha256"]
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        print(f"cannot tamper receipt: {exc}")
        return 1
    new_value = ("0" if old_value[0] != "0" else "1") + old_value[1:]
    receipt["provider_events"][0]["payload_sha256"] = new_value
    target = source.with_name(f"{source.stem}.tampered{source.suffix}")
    target.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("Changed field: provider_events[0].payload_sha256")
    print(f"Expected: {old_value}")
    print(f"Found:    {new_value}")
    result = verify.run([str(target)])
    if result == 0:
        print("ERROR: tampered receipt unexpectedly verified")
        return 1
    print(f"Tampered copy: {target}")
    return 0
