#!/usr/bin/env python3
"""Refresh generated review data while retaining order and valid judgments."""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import sys
from pathlib import Path


AI_FIELDS = [
    "ai_policy_labels", "ai_policy_titles", "ai_reason", "ai_confidence",
    "ai_model", "ai_rules_version",
]
HUMAN_FIELDS = [
    "human_policy_labels", "human_reason", "human_verified", "annotator", "reviewed_at",
]
PRESERVED_FIELDS = ["review_batch", *AI_FIELDS, *HUMAN_FIELDS]


def refresh_rows(
    generated_rows: list[dict[str, str]], current_rows: list[dict[str, str]]
) -> tuple[list[dict[str, str]], list[str]]:
    generated_by_id = {row["post_id"]: row for row in generated_rows}
    current_by_id = {row["post_id"]: row for row in current_rows}
    if len(generated_by_id) != len(generated_rows):
        raise ValueError("generated review contains duplicate post_id values")
    if len(current_by_id) != len(current_rows):
        raise ValueError("current review contains duplicate post_id values")
    if set(generated_by_id) != set(current_by_id):
        missing = len(set(generated_by_id) - set(current_by_id))
        extra = len(set(current_by_id) - set(generated_by_id))
        raise ValueError(f"post_id set differs: missing={missing}, extra={extra}")

    refreshed: list[dict[str, str]] = []
    invalidated: list[str] = []
    for current in current_rows:
        generated = generated_by_id[current["post_id"]]
        row = dict(generated)
        row["review_batch"] = current["review_batch"]
        if generated["analysis_text"] == current["analysis_text"]:
            for field in [*AI_FIELDS, *HUMAN_FIELDS]:
                row[field] = current.get(field, "")
        else:
            invalidated.append(current["post_id"])
            for field in [*AI_FIELDS, *HUMAN_FIELDS]:
                row[field] = ""
        refreshed.append(row)
    return refreshed, invalidated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generated", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    args = parser.parse_args()
    try:
        with args.generated.open(encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            fields = list(reader.fieldnames or [])
            generated_rows = list(reader)
        with args.current.open(encoding="utf-8", newline="") as file:
            current_rows = list(csv.DictReader(file))
        refreshed, invalidated = refresh_rows(generated_rows, current_rows)
        backup = args.current.with_suffix(args.current.suffix + ".before_note_tweet_refresh")
        if not backup.exists():
            shutil.copy2(args.current, backup)
            backup.chmod(0o600)
        temporary = args.current.with_suffix(args.current.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(refreshed)
        temporary.chmod(0o600)
        os.replace(temporary, args.current)
    except (OSError, KeyError, ValueError) as exc:
        print(f"投稿レビュー表の更新に失敗しました: {exc}", file=sys.stderr)
        return 1
    print(
        f"refreshed {len(refreshed)} rows; invalidated {len(invalidated)} changed-text "
        f"judgments; backup={backup}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
