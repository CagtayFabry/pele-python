"""Validate the data boundary without duplicating Pele's option schema."""

import json
import math
from typing import Any


def _validate(value: Any, active: set[int]) -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, (int, float)):
        try:
            finite = math.isfinite(value)
        except OverflowError:
            finite = False
        if not finite:
            raise ValueError("options must contain only finite JSON numbers")
        return
    if isinstance(value, (dict, list, tuple)):
        identity = id(value)
        if identity in active:
            raise ValueError("options must not contain circular references")
        active.add(identity)
        try:
            if isinstance(value, dict):
                for key, item in value.items():
                    if not isinstance(key, str):
                        raise TypeError("JSON option object keys must be strings")
                    _validate(item, active)
            else:
                for item in value:
                    _validate(item, active)
        finally:
            active.remove(identity)
        return
    raise TypeError(f"options must be JSON data; received {type(value).__name__}")


def encode_options(options: dict[str, Any]) -> str:
    for name in ("measurer", "icons", "math"):
        if options.get(name) is not None:
            raise TypeError(f"Pele option {name!r} requires a callback and is not supported")
    _validate(options, set())
    return json.dumps(options, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
