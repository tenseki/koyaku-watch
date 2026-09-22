#!/usr/bin/env python3
"""Restore generated review columns while preserving human-entered columns."""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import sys
from pathlib import Path


HUMAN_FIELDS = [
    "human_policy_labels", "human_reason", "human_verified", "annotator", "reviewed_at"
]


def restore_rows(
    generated_rows: list[dict[str, str]], current_rows: list[dict[str, str]]
) -> list[dict[str, str]]:
    current_by_url = {row["post_url"]: row for row in current_rows}
    if len(current_by_url) != len(current_rows):
        raise ValueError("current review contains duplicate post_url values")
    generated_urls = {row["post_url"] for row in generated_rows}
    if generated_urls != set(current_by_url):
        missing = len(generated_urls - set(current_by_url))
        extra = len(set(current_by_url) - generated_urls)
        raise ValueError(f"post_url set differs: missing={missing}, extra={extra}")
    restored: list[dict[str, str]] = []
    for generated in generated_rows:
        row = dict(generated)
        current = current_by_url[generated["post_url"]]
        for field in HUMAN_FIELDS:
            row[field] = current.get(field, "")
        restored.append(row)
    return restored


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generated", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    args = parser.parse_args()
    try:
        with args.generated.open(encoding="utf-8", newline="") as file:
            generated_reader = csv.DictReader(file)
            fields = list(generated_reader.fieldnames or [])
            generated_rows = list(generated_reader)
        with args.current.open(encoding="utf-8", newline="") as file:
            current_rows = list(csv.DictReader(file))
        restored = restore_rows(generated_rows, current_rows)
        backup = args.current.with_suffix(args.current.suffix + ".before_restore")
        shutil.copy2(args.current, backup)
        backup.chmod(0o600)
        temporary = args.current.with_suffix(args.current.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(restored)
        temporary.chmod(0o600)
        os.replace(temporary, args.current)
    except (OSError, KeyError, ValueError) as exc:
        print(f"投稿レビュー表の復元に失敗しました: {exc}", file=sys.stderr)
        return 1
    print(
        f"restored {len(restored)} rows and preserved {len(HUMAN_FIELDS)} human fields; "
        f"backup={backup}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
