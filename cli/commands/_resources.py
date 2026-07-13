"""Wheel-safe access to the small public runtime data bundle."""
from __future__ import annotations

import os
import shutil
import tempfile
from importlib import resources
from pathlib import Path
from typing import Any

SOURCE_ROOT = Path(__file__).resolve().parents[2]
_TEMP_RESOURCES: list[tempfile.TemporaryDirectory] = []


def _copy_tree(source: Any, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for child in source.iterdir():
        target = destination / child.name
        if child.is_dir():
            _copy_tree(child, target)
        else:
            with resources.as_file(child) as file_path:
                shutil.copyfile(file_path, target)


def _materialized_tree(package: str, *parts: str) -> Path:
    temp = tempfile.TemporaryDirectory(prefix="apl-sidecar-")
    _TEMP_RESOURCES.append(temp)
    root = Path(temp.name)
    source = resources.files(package).joinpath(*parts)
    destination = root.joinpath(package, *parts)
    _copy_tree(source, destination)
    return destination


def bundled_scenario_path(scenario_id: str) -> Path:
    source = SOURCE_ROOT / "examples" / scenario_id
    if source.is_dir():
        return source
    return _materialized_tree("examples", scenario_id)


def playground_root() -> Path:
    if (SOURCE_ROOT / ".git").is_dir() and (
            SOURCE_ROOT / "app" / "local_playground").is_dir():
        return SOURCE_ROOT
    playground = _materialized_tree("app", "local_playground")
    return playground.parents[1]


def read_spec_text(name: str) -> str:
    source = SOURCE_ROOT / "spec" / name
    if source.is_file():
        return source.read_text(encoding="utf-8")
    return resources.files("spec").joinpath(name).read_text(encoding="utf-8")


def read_spec_bytes(name: str) -> bytes:
    source = SOURCE_ROOT / "spec" / name
    if source.is_file():
        return source.read_bytes()
    return resources.files("spec").joinpath(name).read_bytes()


def user_key_dir() -> Path:
    configured = os.environ.get("APL_KEY_DIR")
    return Path(configured).expanduser() if configured else Path.home() / ".apl-sidecar" / "keys"