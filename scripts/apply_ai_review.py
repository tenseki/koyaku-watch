#!/usr/bin/env python3
"""Apply a versioned AI suggestion batch to a post-review CSV."""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

try:
    from policy_catalog import select_policy_rows
    from validate_post_review import parse_policy_labels
except ModuleNotFoundError:  # Imported as scripts.apply_ai_review in tests.
    from scripts.policy_catalog import select_policy_rows
    from scripts.validate_post_review import parse_policy_labels


def apply_suggestions(
    rows: list[dict[str, str]], suggestions: list[dict[str, str]],
    policy_titles: dict[str, str], allowed_labels: set[str], model: str,
    rules_version: str,
) -> list[str]:
    errors: list[str] = []
    by_post = {row["post_id"]: row for row in rows}
    seen: set[str] = set()
    for suggestion in suggestions:
        error_count = len(errors)
        post_id = suggestion.get("post_id", "").strip()
        if post_id in seen:
            errors.append(f"duplicate suggestion post_id: {post_id}")
            continue
        seen.add(post_id)
        if post_id not in by_post:
            errors.append(f"unknown suggestion post_id: {post_id}")
            continue
        labels = suggestion.get("policy_labels", "").strip()
        label_errors = parse_policy_labels(labels, set(policy_titles), allowed_labels)
        errors.extend(f"{post_id}: {error}" for error in label_errors)
        confidence = suggestion.get("confidence", "").strip()
        if confidence not in {"high", "medium", "low"}:
            errors.append(f"{post_id}: invalid confidence: {confidence}")
        if not suggestion.get("reason", "").strip():
            errors.append(f"{post_id}: reason is required")
        if len(errors) > error_count:
            continue
        policy_ids = [] if labels == "none" else [
            item.split("=", 1)[0].strip() for item in labels.split("|")
        ]
        row = by_post[post_id]
        row["ai_policy_labels"] = labels
        row["ai_policy_titles"] = "|".join(policy_titles[x] for x in policy_ids)
        row["ai_reason"] = suggestion["reason"].strip()
        row["ai_confidence"] = confidence
        row["ai_model"] = model
        row["ai_rules_version"] = rules_version
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--analysis-config", type=Path,
        default=root / "config" / "analysis_mvp_2026.json",
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--suggestions", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--rules-version", required=True)
    args = parser.parse_args()
    try:
        config = json.loads(args.analysis_config.read_text(encoding="utf-8"))
        policy_path = Path(config["policy"]["config"])
        if not policy_path.is_absolute():
            policy_path = (args.analysis_config.parent / policy_path).resolve()
        _, policy_rows, _ = select_policy_rows(
            policy_path, config["policy"]["formal_mvp_set"]
        )
        titles = {row["policy_id"]: row["title"] for row in policy_rows}
        allowed = set(config["human_labeling"]["allowed_labels"]) - {"none"}
        suggestions = json.loads(args.suggestions.read_text(encoding="utf-8"))
        with args.input.open(encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            fields = list(reader.fieldnames or [])
            rows = list(reader)
        errors = apply_suggestions(
            rows, suggestions, titles, allowed, args.model, args.rules_version
        )
        if errors:
            raise ValueError("; ".join(errors))
        temporary = args.input.with_suffix(args.input.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        temporary.chmod(0o600)
        os.replace(temporary, args.input)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"AI提案の適用に失敗しました: {exc}", file=sys.stderr)
        return 1
    print(f"applied {len(suggestions)} AI suggestions to {args.input}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
