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


def _source_checkout() -> bool:
    """True only when running from the actual repo checkout. Installed wheels
    live in site-packages, where sibling 'examples'/'spec' directories may
    belong to OTHER packages — without this marker gate they would silently
    shadow our bundled assets (including the demo public key)."""
    return (SOURCE_ROOT / ".git").is_dir()


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
    if _source_checkout():
        source = SOURCE_ROOT / "examples" / scenario_id
        if source.is_dir():
            return source
    return _materialized_tree("examples", scenario_id)


def playground_root() -> Path:
    if _source_checkout() and (
            SOURCE_ROOT / "app" / "local_playground").is_dir():
        return SOURCE_ROOT
    playground = _materialized_tree("app", "local_playground")
    return playground.parents[1]


def read_spec_text(name: str) -> str:
    if _source_checkout():
        source = SOURCE_ROOT / "spec" / name
        if source.is_file():
            return source.read_text(encoding="utf-8")
    return resources.files("spec").joinpath(name).read_text(encoding="utf-8")


def read_spec_bytes(name: str) -> bytes:
    if _source_checkout():
        source = SOURCE_ROOT / "spec" / name
        if source.is_file():
            return source.read_bytes()
    return resources.files("spec").joinpath(name).read_bytes()


def spec_key_path(name: str) -> Path:
    """Filesystem path to a packaged spec asset (e.g. the demo PUBLIC key).

    From a source checkout this is the on-disk spec/ file. From an installed
    wheel the resource is materialized to a temp file so callers that need a
    real path (the verifier takes a PEM path, not bytes) always get one.
    Raises FileNotFoundError when the asset does not exist.
    """
    if _source_checkout():
        source = SOURCE_ROOT / "spec" / name
        if source.is_file():
            return source
        raise FileNotFoundError(name)
    resource = resources.files("spec").joinpath(name)
    if not resource.is_file():
        raise FileNotFoundError(name)
    temp = tempfile.TemporaryDirectory(prefix="apl-sidecar-key-")
    _TEMP_RESOURCES.append(temp)
    target = Path(temp.name) / name
    with resources.as_file(resource) as file_path:
        shutil.copyfile(file_path, target)
    return target


def user_key_dir() -> Path:
    configured = os.environ.get("APL_KEY_DIR")
    return Path(configured).expanduser() if configured else Path.home() / ".apl-sidecar" / "keys"