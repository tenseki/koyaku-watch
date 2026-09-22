#!/usr/bin/env python3
"""Apply explicit human-review corrections to a post-review CSV."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path


EDITABLE_FIELDS = {
    "human_policy_labels", "human_reason", "human_verified", "annotator", "reviewed_at"
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--corrections", type=Path)
    parser.add_argument("--replace-annotator")
    parser.add_argument("--annotator-with")
    parser.add_argument("--complete-batch")
    parser.add_argument("--completion-annotator")
    parser.add_argument("--completion-date")
    parser.add_argument("--normalize-reviewed-at", action="store_true")
    args = parser.parse_args()
    try:
        if (
            args.corrections is None
            and args.replace_annotator is None
            and args.complete_batch is None
            and not args.normalize_reviewed_at
        ):
            parser.error(
                "--corrections, --replace-annotator, --complete-batch, or "
                "--normalize-reviewed-at is required"
            )
        if (args.replace_annotator is None) != (args.annotator_with is None):
            parser.error("--replace-annotator and --annotator-with must be used together")
        if args.complete_batch is not None and (
            args.completion_annotator is None or args.completion_date is None
        ):
            parser.error(
                "--complete-batch requires --completion-annotator and --completion-date"
            )
        corrections = (
            json.loads(args.corrections.read_text(encoding="utf-8"))
            if args.corrections is not None
            else []
        )
        with args.input.open(encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            fields = list(reader.fieldnames or [])
            rows = list(reader)
        by_url = {row["post_url"]: row for row in rows}
        for correction in corrections:
            post_url = correction["post_url"]
            if post_url not in by_url:
                raise ValueError(f"unknown post_url: {post_url}")
            unknown = set(correction) - EDITABLE_FIELDS - {"post_url"}
            if unknown:
                raise ValueError(f"non-human fields cannot be edited: {sorted(unknown)}")
            for field in EDITABLE_FIELDS:
                if field in correction:
                    by_url[post_url][field] = correction[field]
        metadata_corrections = 0
        if args.replace_annotator is not None:
            for row in rows:
                if row["annotator"] == args.replace_annotator:
                    row["annotator"] = args.annotator_with
                    metadata_corrections += 1
        completed_rows = 0
        if args.complete_batch is not None:
            datetime.strptime(args.completion_date, "%Y-%m-%d")
            for row in rows:
                if row["review_batch"] != args.complete_batch:
                    continue
                if not row["human_policy_labels"] or not row["human_reason"]:
                    raise ValueError(
                        f"batch {args.complete_batch} has incomplete human fields: "
                        f"{row['post_url']}"
                    )
                if not row["human_verified"]:
                    row["human_verified"] = "true"
                    row["annotator"] = args.completion_annotator
                    row["reviewed_at"] = args.completion_date
                    completed_rows += 1
        normalized_dates = 0
        if args.normalize_reviewed_at:
            for row in rows:
                value = row["reviewed_at"].strip()
                if not value:
                    continue
                for date_format in (
                    "%Y-%m-%d",
                    "%Y-%b-%d",
                    "%Y/%m/%d",
                    "%m-%d-%y",
                ):
                    try:
                        normalized = datetime.strptime(value, date_format).strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        normalized = ""
                if not normalized:
                    raise ValueError(f"unsupported reviewed_at value: {value}")
                if normalized != value:
                    row["reviewed_at"] = normalized
                    normalized_dates += 1
        temporary = args.input.with_suffix(args.input.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        temporary.chmod(0o600)
        os.replace(temporary, args.input)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"人手判定の訂正に失敗しました: {exc}", file=sys.stderr)
        return 1
    print(
        f"applied {len(corrections)} row corrections and "
        f"{metadata_corrections} annotator corrections; completed "
        f"{completed_rows} rows and normalized {normalized_dates} dates in {args.input}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
