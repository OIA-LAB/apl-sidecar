"""Minimal JSON-Schema subset checker (no external dependency).

Supports exactly what spec/*.schema.json uses: type, required, properties,
items, enum, const, pattern, minimum, maximum, minLength, minItems, anyOf.
"""
from __future__ import annotations

import re

_TYPES = {"object": dict, "array": list, "string": str, "boolean": bool,
          "integer": int, "null": type(None)}


def check(instance, schema, path="$"):
    """Returns a list of error strings (empty = valid)."""
    errors = []
    if "anyOf" in schema:
        branches = [check(instance, s, path) for s in schema["anyOf"]]
        if not any(not b for b in branches):
            errors.append(f"{path}: matches no anyOf branch")
        return errors
    t = schema.get("type")
    if t:
        if t == "number":
            ok = isinstance(instance, (int, float)) and not isinstance(instance, bool)
        elif t == "integer":
            ok = isinstance(instance, int) and not isinstance(instance, bool)
        elif t == "boolean":
            ok = isinstance(instance, bool)
        else:
            ok = isinstance(instance, _TYPES[t]) and not (
                t != "boolean" and isinstance(instance, bool))
        if not ok:
            return [f"{path}: expected {t}, got {type(instance).__name__}"]
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: {instance!r} not in enum")
    if isinstance(instance, str):
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append(f"{path}: does not match {schema['pattern']}")
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append(f"{path}: shorter than minLength")
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: below minimum")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: above maximum")
    if isinstance(instance, dict):
        for req in schema.get("required", []):
            if req not in instance:
                errors.append(f"{path}: missing required {req!r}")
        for key, sub in schema.get("properties", {}).items():
            if key in instance:
                errors.extend(check(instance[key], sub, f"{path}.{key}"))
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: fewer than minItems")
        if "items" in schema:
            for i, item in enumerate(instance):
                errors.extend(check(item, schema["items"], f"{path}[{i}]"))
    return errors
