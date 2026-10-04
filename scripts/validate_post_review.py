#!/usr/bin/env python3
"""Validate one-row-per-post AI/human review data."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

try:
    from policy_catalog import select_policy_rows
except ModuleNotFoundError:  # Imported as scripts.validate_post_review in tests.
    from scripts.policy_catalog import select_policy_rows


def parse_policy_labels(
    value: str, allowed_policy_ids: set[str], allowed_labels: set[str]
) -> list[str]:
    value = value.strip()
    if not value:
        return []
    if value == "none":
        return []
    errors: list[str] = []
    seen: set[str] = set()
    for item in value.split("|"):
        if "=" not in item:
            errors.append(f"invalid assignment: {item}")
            continue
        policy_id, label = (part.strip() for part in item.split("=", 1))
        if policy_id not in allowed_policy_ids:
            errors.append(f"unknown policy_id: {policy_id}")
        if label not in allowed_labels:
            errors.append(f"invalid mention_level: {label}")
        if policy_id in seen:
            errors.append(f"duplicate policy_id: {policy_id}")
        seen.add(policy_id)
    return errors


def validate_rows(
    rows: list[dict[str, str]], config: dict, policy_ids: set[str]
) -> list[str]:
    labels = set(config["human_labeling"]["allowed_labels"]) - {"none"}
    confidence = set(config["post_review"]["allowed_confidence"])
    errors: list[str] = []
    seen: set[str] = set()
    for line_number, row in enumerate(rows, start=2):
        post_id = row.get("post_id", "").strip()
        if not post_id:
            errors.append(f"line {line_number}: post_id is required")
        elif post_id in seen:
            errors.append(f"line {line_number}: duplicate post_id: {post_id}")
        seen.add(post_id)

        ai_value = row.get("ai_policy_labels", "").strip()
        human_value = row.get("human_policy_labels", "").strip()
        for error in parse_policy_labels(ai_value, policy_ids, labels):
            errors.append(f"line {line_number}: ai_policy_labels: {error}")
        for error in parse_policy_labels(human_value, policy_ids, labels):
            errors.append(f"line {line_number}: human_policy_labels: {error}")

        if ai_value:
            if row.get("ai_confidence", "").strip() not in confidence:
                errors.append(f"line {line_number}: AI label requires valid ai_confidence")
            if not row.get("ai_model", "").strip():
                errors.append(f"line {line_number}: AI label requires ai_model")
            if not row.get("ai_rules_version", "").strip():
                errors.append(f"line {line_number}: AI label requires ai_rules_version")

        verified = row.get("human_verified", "").strip().lower()
        if verified not in {"", "true", "false"}:
            errors.append(f"line {line_number}: human_verified must be true or false")
        if verified == "true":
            if not human_value:
                errors.append(f"line {line_number}: verified row requires human_policy_labels")
            if not row.get("annotator", "").strip():
                errors.append(f"line {line_number}: verified row requires annotator")
            if not row.get("reviewed_at", "").strip():
                errors.append(f"line {line_number}: verified row requires reviewed_at")
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--analysis-config", type=Path,
        default=root / "config" / "analysis_mvp_2026.json",
    )
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    try:
        config = json.loads(args.analysis_config.read_text(encoding="utf-8"))
        policy_path = Path(config["policy"]["config"])
        if not policy_path.is_absolute():
            policy_path = (args.analysis_config.parent / policy_path).resolve()
        policy_set = config["policy"].get("formal_mvp_set") or config["policy"].get("formal_set")
        if not policy_set:
            raise ValueError("policy config requires formal_mvp_set or formal_set")
        _, policy_rows, _ = select_policy_rows(policy_path, policy_set)
        with args.input.open(encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        errors = validate_rows(rows, config, {row["policy_id"] for row in policy_rows})
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"投稿レビュー検証に失敗しました: {exc}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        print(f"投稿レビュー検証: {len(errors)}件のエラー", file=sys.stderr)
        return 1
    ai_count = sum(bool(row.get("ai_policy_labels", "").strip()) for row in rows)
    human_count = sum(row.get("human_verified", "").strip().lower() == "true" for row in rows)
    print(
        f"投稿レビュー検証: {len(rows)}投稿 / AI提案{ai_count} / "
        f"人手確認{human_count} / エラー0件"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
