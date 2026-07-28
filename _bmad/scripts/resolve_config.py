#!/usr/bin/env python3
"""Resolve child-local BMad TOML configuration without third-party packages."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

try:
    import tomllib
except ImportError:
    sys.exit("Python 3.11+ is required")


def keyed_field(items):
    if not items or not all(isinstance(item, dict) for item in items):
        return None
    for field in ("code", "id"):
        if all(field in item for item in items):
            return field
    return None


def merge(left, right):
    if isinstance(left, dict) and isinstance(right, dict):
        result = dict(left)
        for key, value in right.items():
            result[key] = merge(result[key], value) if key in result else value
        return result
    if isinstance(left, list) and isinstance(right, list):
        field = keyed_field(left + right)
        if not field:
            return left + right
        result = [dict(item) for item in left]
        positions = {item[field]: index for index, item in enumerate(result)}
        for item in right:
            if item[field] in positions:
                result[positions[item[field]]] = dict(item)
            else:
                positions[item[field]] = len(result)
                result.append(dict(item))
        return result
    return right


def load(path: Path, required=False):
    if not path.exists():
        if required:
            raise SystemExit(f"required config file not found: {path}")
        return {}
    try:
        with path.open("rb") as stream:
            return tomllib.load(stream)
    except tomllib.TOMLDecodeError as error:
        raise SystemExit(f"invalid TOML in {path}: {error}") from error


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--project-root", "-p", required=True)
    parser.add_argument("--key", "-k", action="append", default=[])
    args = parser.parse_args()
    root = Path(args.project_root).resolve()
    bmad = root / "_bmad"
    config = load(bmad / "config.toml", required=True)
    for name in ("config.user.toml", "custom/config.toml", "custom/config.user.toml"):
        config = merge(config, load(bmad / name))
    if args.key:
        output = {}
        for dotted in args.key:
            value = config
            for part in dotted.split("."):
                if not isinstance(value, dict) or part not in value:
                    break
                value = value[part]
            else:
                output[dotted] = value
    else:
        output = config
    text = json.dumps(output, indent=2, ensure_ascii=False)
    print(text.replace("{project-root}", str(root)))


if __name__ == "__main__":
    main()
