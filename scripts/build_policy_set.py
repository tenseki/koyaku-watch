#!/usr/bin/env python3
"""Export a named, ordered policy set for the comparison pipeline."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from policy_catalog import load_config, select_policy_rows


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a policy CSV from a named set in policy_sets_2026.json."
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--set", dest="set_name")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--list-sets", action="store_true", help="List available sets and exit."
    )
    args = parser.parse_args()

    config = load_config(args.config)
    if args.list_sets:
        for name, definition in config["sets"].items():
            marker = " (default)" if name == config["default_set"] else ""
            print(f"{name}{marker}: {definition.get('description', '')}")
        return

    set_name = args.set_name or config["default_set"]
    if args.output is None:
        parser.error("--output is required unless --list-sets is used")

    fields, rows, _ = select_policy_rows(args.config, set_name)
    output_fields = ["policy_set", *fields]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=output_fields)
        writer.writeheader()
        writer.writerows({"policy_set": set_name, **row} for row in rows)

    print(f"wrote {len(rows)} policies from '{set_name}' to {args.output}")


if __name__ == "__main__":
    main()
