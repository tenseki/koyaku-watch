#!/usr/bin/env python3
"""Evaluate retrieval runs against verified post-level policy labels."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Iterable


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def parse_labels(value: str) -> dict[str, str]:
    value = value.strip()
    if not value or value == "none":
        return {}
    labels: dict[str, str] = {}
    for item in value.split("|"):
        policy_id, separator, level = item.partition("=")
        policy_id = policy_id.strip()
        level = level.strip()
        if not separator or not policy_id or not level:
            raise ValueError(f"invalid policy label: {item!r}")
        labels[policy_id] = level
    return labels


def positive_pairs(
    review_rows: Iterable[dict[str, str]], levels: set[str]
) -> set[tuple[str, str]]:
    output: set[tuple[str, str]] = set()
    for row in review_rows:
        if row.get("human_verified", "").strip().lower() != "true":
            raise ValueError(f"unverified review row: {row.get('post_id', '')}")
        for policy_id, level in parse_labels(row["human_policy_labels"]).items():
            if level in levels:
                output.add((policy_id, row["post_id"]))
    return output


def selection_metrics(
    rows: list[dict[str, str]],
    positives: set[tuple[str, str]],
    *,
    top_k: int | None = None,
    include_keywords: bool = False,
) -> dict[str, int | float]:
    selected: set[tuple[str, str]] = set()
    selected_posts: set[str] = set()
    for row in rows:
        by_rank = top_k is not None and int(row["rank"]) <= top_k
        by_keyword = include_keywords and bool(row["keyword_matches"].strip())
        if by_rank or by_keyword:
            pair = (row["policy_id"], row["post_id"])
            selected.add(pair)
            selected_posts.add(row["post_id"])
    recovered = len(selected & positives)
    return {
        "positive_pairs": len(positives),
        "recovered_positive_pairs": recovered,
        "recall": recovered / len(positives) if positives else 0.0,
        "selected_pairs": len(selected),
        "selected_unique_posts": len(selected_posts),
        "pair_precision": recovered / len(selected) if selected else 0.0,
    }


def evaluate_run(
    rows: list[dict[str, str]],
    review_rows: list[dict[str, str]],
    views: dict[str, set[str]],
    top_ks: list[int],
) -> dict[str, object]:
    review_post_ids = {row["post_id"] for row in review_rows}
    run_post_ids = {row["post_id"] for row in rows}
    if run_post_ids != review_post_ids:
        raise ValueError("similarity and review post ID sets differ")
    result: dict[str, object] = {
        "policy_count": len({row["policy_id"] for row in rows}),
        "post_count": len(run_post_ids),
        "pair_count": len(rows),
        "views": {},
    }
    output_views: dict[str, object] = result["views"]  # type: ignore[assignment]
    for view_name, levels in views.items():
        positives = positive_pairs(review_rows, levels)
        metrics: dict[str, object] = {
            "keyword_only": selection_metrics(
                rows, positives, include_keywords=True
            )
        }
        for top_k in top_ks:
            metrics[f"top_{top_k}"] = selection_metrics(
                rows, positives, top_k=top_k
            )
            metrics[f"keyword_or_top_{top_k}"] = selection_metrics(
                rows, positives, top_k=top_k, include_keywords=True
            )
        output_views[view_name] = metrics
    return result


def parse_named_path(value: str) -> tuple[str, Path]:
    name, separator, raw_path = value.partition("=")
    if not separator or not name or not raw_path:
        raise argparse.ArgumentTypeError("expected NAME=PATH")
    return name, Path(raw_path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--analysis-config", type=Path, required=True)
    parser.add_argument(
        "--similarity", type=parse_named_path, action="append", required=True
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument("--top-k", type=int, nargs="+", default=[1, 3, 5, 10, 20])
    args = parser.parse_args()

    config = json.loads(args.analysis_config.read_text(encoding="utf-8"))
    configured_views = {
        name: set(levels) for name, levels in config["analysis_views"].items()
    }
    configured_views["any_policy_mention"] = {
        "specific_measure", "policy_direction", "topic_only"
    }
    review_rows = read_csv(args.review)
    output = {
        "review": str(args.review),
        "verified_post_count": len(review_rows),
        "top_k_values": args.top_k,
        "runs": {
            name: evaluate_run(
                read_csv(path), review_rows, configured_views, args.top_k
            )
            for name, path in args.similarity
        },
    }
    rendered = json.dumps(output, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
        args.output.chmod(0o600)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
