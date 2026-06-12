"""CLI output formatting and exit codes."""

from __future__ import annotations

import json
import sys
from typing import Any, Iterable


EXIT_OK = 0
EXIT_ERROR = 1
EXIT_POLICY = 2


def emit(data: Any, *, fmt: str = "table", quiet: bool = False) -> None:
    """Writes result to stdout."""
    if quiet:
        return
    if fmt == "json":
        print(json.dumps(data, indent=2, default=str))
        return
    if isinstance(data, dict):
        _emit_dict_table(data)
        return
    if isinstance(data, list):
        _emit_list_table(data)
        return
    print(data)


def emit_lines(lines: Iterable[str], *, quiet: bool = False) -> None:
    if quiet:
        return
    for line in lines:
        print(line)


def emit_error(message: str) -> None:
    print(message, file=sys.stderr)


def _emit_dict_table(data: dict[str, Any]) -> None:
    for key, value in data.items():
        if isinstance(value, (dict, list)):
            print(f"{key}:")
            if isinstance(value, list):
                _emit_list_table(value, indent=2)
            else:
                for sub_key, sub_value in value.items():
                    print(f"  {sub_key}: {sub_value}")
        else:
            print(f"{key}: {value}")


def _emit_list_table(rows: list[Any], *, indent: int = 0) -> None:
    if not rows:
        prefix = " " * indent
        print(f"{prefix}(empty)")
        return
    if not isinstance(rows[0], dict):
        prefix = " " * indent
        for row in rows:
            print(f"{prefix}{row}")
        return

    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)

    prefix = " " * indent
    print(f"{prefix}{' | '.join(keys)}")
    print(f"{prefix}{'-+-'.join('-' * len(k) for k in keys)}")
    for row in rows:
        values = [str(row.get(key, "")) for key in keys]
        print(f"{prefix}{' | '.join(values)}")
