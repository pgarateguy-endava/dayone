#!/usr/bin/env python3
"""Append-only project memory helper for child-local BMad artifacts."""
from __future__ import annotations

import argparse
from datetime import datetime
import os
from pathlib import Path
import tempfile


def target(args):
    return Path(args.path) if args.path else Path(args.workspace) / ".memlog.md"


def write_atomic(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
        temporary = Path(stream.name)
    os.replace(temporary, path)


def touch(text):
    stamp = datetime.now().strftime("%Y-%m-%dT%H:%M")
    if "updated:" in text:
        lines = [f"updated: {stamp}" if line.startswith("updated:") else line for line in text.splitlines()]
        return "\n".join(lines) + "\n"
    return text.replace("---\n\n", f"updated: {stamp}\n---\n\n", 1)


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("init", "append", "set"):
        action = sub.add_parser(command)
        group = action.add_mutually_exclusive_group(required=True)
        group.add_argument("--workspace")
        group.add_argument("--path")
        if command == "init":
            action.add_argument("--field", action="append", default=[])
        elif command == "append":
            action.add_argument("--text", required=True)
            action.add_argument("--type")
        else:
            action.add_argument("--key", required=True)
            action.add_argument("--value", required=True)
    args = parser.parse_args()
    path = target(args)
    if args.command == "init":
        if path.exists():
            raise SystemExit(f"already exists: {path}")
        fields = []
        for field in args.field:
            if "=" not in field:
                raise SystemExit(f"--field expects key=value: {field}")
            key, value = field.split("=", 1)
            fields.append(f"{key}: {value}")
        write_atomic(path, "---\n" + "\n".join(fields) + "\nupdated: " + datetime.now().strftime("%Y-%m-%dT%H:%M") + "\n---\n\n")
        return
    if not path.exists():
        raise SystemExit(f"missing memlog: {path}")
    text = path.read_text(encoding="utf-8")
    if args.command == "append":
        label = f"({args.type}) " if args.type else ""
        updated = text.rstrip("\n") + f"\n- {label}{args.text.strip()}\n"
    else:
        lines = text.splitlines()
        try:
            index = next(i for i, line in enumerate(lines) if line.startswith(f"{args.key}:"))
        except StopIteration:
            lines.insert(1, f"{args.key}: {args.value}")
        else:
            lines[index] = f"{args.key}: {args.value}"
        updated = "\n".join(lines) + "\n"
    write_atomic(path, touch(updated))


if __name__ == "__main__":
    main()
