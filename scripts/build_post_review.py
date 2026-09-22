#!/usr/bin/env python3
"""Build a one-row-per-post worksheet for iterative AI/human review."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path


REVIEW_FIELDS = [
    "review_batch", "review_stratum", "post_id", "candidate_key", "x_handle",
    "created_at", "post_type", "post_url", "analysis_text", "screening_hints",
    "retrieval_policy_ids", "retrieval_policy_titles", "retrieval_reasons",
    "ai_policy_labels", "ai_policy_titles", "ai_reason", "ai_confidence",
    "ai_model", "ai_rules_version", "human_policy_labels", "human_reason",
    "human_verified", "annotator", "reviewed_at",
]

SCREENING_PATTERNS = {
    "election_call": re.compile(r"期日前投票|投票(?:日|所|へ|を|に|して|お願い|よろしく)"),
    "campaign_event": re.compile(r"街頭演説|個人演説会|演説会|街頭活動|街頭に"),
}


def stable_key(seed: int, post_id: str) -> str:
    return hashlib.sha256(f"{seed}:{post_id}".encode()).hexdigest()


def build_retrieval_index(
    similarity_path: Path, top_k: int
) -> tuple[dict[str, dict[str, set[str]]], dict[str, str]]:
    by_post: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    titles: dict[str, str] = {}
    with similarity_path.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file):
            policy_id = row["policy_id"]
            titles[policy_id] = row["policy_title"]
            if int(row["rank"]) <= top_k:
                by_post[row["post_id"]][policy_id].add("similarity_top")
            if row["keyword_matches"].strip():
                by_post[row["post_id"]][policy_id].add("keyword_match")
    return by_post, titles


def choose_first_batch(
    rows: list[dict[str, str]], batch_size: int, seed: int
) -> set[str]:
    quotas = {
        "retrieval_and_generic": 10,
        "retrieval_candidate": 15,
        "generic_hint": 10,
        "baseline": 5,
    }
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[row["review_stratum"]].append(row)
    for group in groups.values():
        group.sort(key=lambda row: stable_key(seed, row["post_id"]))
    selected: list[dict[str, str]] = []
    for stratum, quota in quotas.items():
        selected.extend(groups[stratum][:quota])
    if len(selected) < batch_size:
        chosen = {row["post_id"] for row in selected}
        remaining = [row for row in rows if row["post_id"] not in chosen]
        remaining.sort(key=lambda row: stable_key(seed, row["post_id"]))
        selected.extend(remaining[:batch_size - len(selected)])
    return {row["post_id"] for row in selected[:batch_size]}


def build_review_rows(
    post_rows: list[dict[str, str]],
    retrieval: dict[str, dict[str, set[str]]],
    policy_titles: dict[str, str],
    batch_size: int,
    seed: int,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for post in post_rows:
        if post.get("is_analysis_target") != "true":
            continue
        hints = [
            name for name, pattern in SCREENING_PATTERNS.items()
            if pattern.search(post["analysis_text"])
        ]
        candidates = retrieval.get(post["post_id"], {})
        policy_ids = sorted(candidates)
        if policy_ids and hints:
            stratum = "retrieval_and_generic"
        elif policy_ids:
            stratum = "retrieval_candidate"
        elif hints:
            stratum = "generic_hint"
        else:
            stratum = "baseline"
        reasons = [
            f"{policy_id}={'&'.join(sorted(candidates[policy_id]))}"
            for policy_id in policy_ids
        ]
        rows.append({
            "review_batch": "",
            "review_stratum": stratum,
            "post_id": post["post_id"],
            "candidate_key": post["candidate_key"],
            "x_handle": post["x_handle"],
            "created_at": post["created_at"],
            "post_type": post["post_type"],
            "post_url": post["post_url"],
            "analysis_text": post["analysis_text"],
            "screening_hints": "|".join(hints),
            "retrieval_policy_ids": "|".join(policy_ids),
            "retrieval_policy_titles": "|".join(policy_titles[x] for x in policy_ids),
            "retrieval_reasons": "|".join(reasons),
            "ai_policy_labels": "",
            "ai_policy_titles": "",
            "ai_reason": "",
            "ai_confidence": "",
            "ai_model": "",
            "ai_rules_version": "",
            "human_policy_labels": "",
            "human_reason": "",
            "human_verified": "",
            "annotator": "",
            "reviewed_at": "",
        })
    first_ids = choose_first_batch(rows, batch_size, seed)
    first = [row for row in rows if row["post_id"] in first_ids]
    rest = [row for row in rows if row["post_id"] not in first_ids]
    first.sort(key=lambda row: (row["review_stratum"], stable_key(seed, row["post_id"])))
    rest.sort(key=lambda row: stable_key(seed, row["post_id"]))
    ordered = first + rest
    for index, row in enumerate(ordered):
        row["review_batch"] = str(math.floor(index / batch_size) + 1)
    return ordered


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--analysis-config", type=Path,
        default=root / "config" / "analysis_mvp_2026.json",
    )
    parser.add_argument(
        "--posts", type=Path,
        default=root / "data" / "private" / "mvp_posts.processed.csv",
    )
    parser.add_argument(
        "--similarity", type=Path,
        default=root / "data" / "private" / "analysis-mvp-all" / "similarity_all.csv",
    )
    parser.add_argument(
        "--output", type=Path,
        default=root / "data" / "private" / "post_review_working.csv",
    )
    args = parser.parse_args()
    try:
        config = json.loads(args.analysis_config.read_text(encoding="utf-8"))
        review = config["post_review"]
        with args.posts.open(encoding="utf-8", newline="") as file:
            posts = list(csv.DictReader(file))
        retrieval, titles = build_retrieval_index(
            args.similarity, int(config["candidate_sampling"]["top_k"])
        )
        rows = build_review_rows(
            posts, retrieval, titles, int(review["batch_size"]), int(review["random_seed"])
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=REVIEW_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        args.output.chmod(0o600)
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"投稿レビュー表の作成に失敗しました: {exc}", file=sys.stderr)
        return 1
    print(
        f"wrote {len(rows)} posts in {math.ceil(len(rows) / int(review['batch_size']))} "
        f"batches to {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
