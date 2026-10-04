#!/usr/bin/env python3
"""Build public, text-free aggregates from verified post-level reviews."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Iterable

from evaluate_retrieval import parse_labels
from policy_catalog import select_policy_rows


OUTPUT_FIELDS = [
    "policy_id",
    "category",
    "policy_title",
    "specific_measure_posts",
    "specific_measure_density",
    "policy_direction_posts",
    "direction_or_more_posts",
    "direction_or_more_density",
    "topic_only_posts",
    "specific_measure_candidates",
    "direction_or_more_candidates",
    "candidate_count",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def prepare_reviews(
    rows: list[dict[str, str]],
    candidate_keys: set[str],
    policy_ids: set[str],
) -> list[tuple[dict[str, str], dict[str, str]]]:
    seen: set[str] = set()
    prepared: list[tuple[dict[str, str], dict[str, str]]] = []
    for row in rows:
        post_id = row.get("post_id", "").strip()
        if not post_id or post_id in seen:
            raise ValueError(f"missing or duplicate post_id: {post_id!r}")
        seen.add(post_id)
        if row.get("human_verified", "").strip().lower() != "true":
            raise ValueError(f"unverified review row: {post_id}")
        candidate_key = row.get("candidate_key", "").strip()
        if candidate_key not in candidate_keys:
            raise ValueError(f"unknown candidate_key: {candidate_key}")
        labels = parse_labels(row.get("human_policy_labels", ""))
        unknown = sorted(set(labels).difference(policy_ids))
        if unknown:
            raise ValueError(f"unknown policy IDs for {post_id}: {', '.join(unknown)}")
        prepared.append((row, labels))
    if not prepared:
        raise ValueError("review CSV has no rows")
    return prepared


def build_summary(
    review_rows: list[dict[str, str]],
    policy_rows: list[dict[str, str]],
    candidate_rows: list[dict[str, str]],
    policy_set: str,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    policy_ids = {row["policy_id"] for row in policy_rows}
    candidate_keys = {row["candidate_key"] for row in candidate_rows}
    prepared = prepare_reviews(review_rows, candidate_keys, policy_ids)
    post_count = len(prepared)
    candidate_count = len(candidate_keys)

    policy_output: list[dict[str, object]] = []
    for policy in policy_rows:
        policy_id = policy["policy_id"]
        by_level = Counter(
            labels[policy_id]
            for _, labels in prepared
            if policy_id in labels
        )
        specific_candidates = {
            row["candidate_key"]
            for row, labels in prepared
            if labels.get(policy_id) == "specific_measure"
        }
        direction_candidates = {
            row["candidate_key"]
            for row, labels in prepared
            if labels.get(policy_id) in {"specific_measure", "policy_direction"}
        }
        specific = by_level["specific_measure"]
        direction_or_more = specific + by_level["policy_direction"]
        policy_output.append({
            "policy_id": policy_id,
            "category": policy["category"],
            "policy_title": policy["title"],
            "specific_measure_posts": specific,
            "specific_measure_density": specific / post_count,
            "policy_direction_posts": by_level["policy_direction"],
            "direction_or_more_posts": direction_or_more,
            "direction_or_more_density": direction_or_more / post_count,
            "topic_only_posts": by_level["topic_only"],
            "specific_measure_candidates": len(specific_candidates),
            "direction_or_more_candidates": len(direction_candidates),
            "candidate_count": candidate_count,
        })

    specific_posts = [
        row for row, labels in prepared if "specific_measure" in labels.values()
    ]
    direction_posts = [
        row
        for row, labels in prepared
        if any(level in {"specific_measure", "policy_direction"} for level in labels.values())
    ]
    topic_posts = [row for row, labels in prepared if "topic_only" in labels.values()]
    any_posts = [row for row, labels in prepared if labels]
    specific_by_candidate = Counter(row["candidate_key"] for row in specific_posts)
    direction_by_candidate = Counter(row["candidate_key"] for row in direction_posts)
    any_by_candidate = Counter(row["candidate_key"] for row in any_posts)
    volume_by_candidate = Counter(row["candidate_key"] for row, _ in prepared)

    post_type_summary: dict[str, dict[str, int | float]] = {}
    for post_type in sorted({row["post_type"] for row, _ in prepared}):
        typed = [(row, labels) for row, labels in prepared if row["post_type"] == post_type]
        typed_specific = sum("specific_measure" in labels.values() for _, labels in typed)
        post_type_summary[post_type] = {
            "posts": len(typed),
            "specific_measure_posts": typed_specific,
            "specific_measure_density": typed_specific / len(typed),
        }

    level_assignments = Counter(level for _, labels in prepared for level in labels.values())
    result: dict[str, object] = {
        "policy_set": policy_set,
        "post_count": post_count,
        "candidate_count": candidate_count,
        "policy_count": len(policy_rows),
        "posts": {
            "no_selected_policy_mention": post_count - len(any_posts),
            "any_selected_policy_mention": len(any_posts),
            "specific_measure": len(specific_posts),
            "policy_direction_or_more": len(direction_posts),
            "topic_context": len(topic_posts),
        },
        "label_assignments": dict(sorted(level_assignments.items())),
        "policies": {
            "with_specific_measure": sum(
                int(row["specific_measure_posts"] > 0) for row in policy_output
            ),
            "with_direction_or_more": sum(
                int(row["direction_or_more_posts"] > 0) for row in policy_output
            ),
            "with_any_label": sum(
                int(
                    row["direction_or_more_posts"] > 0
                    or row["topic_only_posts"] > 0
                )
                for row in policy_output
            ),
        },
        "candidate_breadth": {
            "with_any_selected_policy_mention": len(any_by_candidate),
            "with_policy_direction_or_more": len(direction_by_candidate),
            "with_specific_measure": len(specific_by_candidate),
            "largest_specific_post_contribution": max(specific_by_candidate.values(), default=0),
            "largest_specific_post_share": (
                max(specific_by_candidate.values(), default=0) / len(specific_posts)
                if specific_posts else 0.0
            ),
            "largest_total_post_contribution": max(volume_by_candidate.values(), default=0),
            "largest_total_post_share": max(volume_by_candidate.values(), default=0) / post_count,
        },
        "post_types": post_type_summary,
    }
    return policy_output, result


def write_csv(path: Path, rows: Iterable[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for row in rows:
            formatted = dict(row)
            for field in ("specific_measure_density", "direction_or_more_density"):
                formatted[field] = f"{float(formatted[field]):.8f}"
            writer.writerow(formatted)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--review", type=Path, default=root / "data/private/post_review_working.csv"
    )
    parser.add_argument(
        "--policy-config", type=Path, default=root / "config/policy_sets_2026.json"
    )
    parser.add_argument("--policy-set", default="mvp_all")
    parser.add_argument(
        "--candidates", type=Path, default=root / "data/mvp_candidates_2026.csv"
    )
    parser.add_argument(
        "--output-csv", type=Path, default=root / "data/mvp_policy_summary_2026.csv"
    )
    parser.add_argument(
        "--output-json", type=Path, default=root / "data/mvp_analysis_summary_2026.json"
    )
    parser.add_argument(
        "--summary-label", default="MVP",
        help="Label used only in the completion message (for example: 全候補者).",
    )
    args = parser.parse_args()

    _, policy_rows, _ = select_policy_rows(args.policy_config, args.policy_set)
    candidate_rows = read_csv(args.candidates)
    policy_output, summary = build_summary(
        read_csv(args.review), policy_rows, candidate_rows, args.policy_set
    )
    write_csv(args.output_csv, policy_output)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        f"{args.summary_label}集計: {summary['post_count']}投稿 / "
        f"{summary['candidate_count']}アカウント / {summary['policy_count']}政策"
    )


if __name__ == "__main__":
    main()
