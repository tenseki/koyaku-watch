#!/usr/bin/env python3
"""Build a reproducible second-pass audit sample from confirmed none labels."""

from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import defaultdict
from pathlib import Path


OUTPUT_FIELDS = [
    "audit_groups", "sample_seed", "post_id", "candidate_key", "x_handle",
    "post_url", "analysis_text", "review_stratum", "ai_confidence",
    "retrieval_policy_ids", "human_policy_labels", "audit_verdict",
    "audit_policy_labels", "audit_reason", "audited_by", "audited_at",
]


def select_audit_rows(
    rows: list[dict[str, str]], sample_size: int, seed: int
) -> tuple[list[dict[str, str]], set[str], set[str]]:
    none_rows = [row for row in rows if row["human_policy_labels"] == "none"]
    if sample_size > len(none_rows):
        raise ValueError("random sample is larger than the none population")
    random_ids = {
        row["post_id"] for row in random.Random(seed).sample(none_rows, sample_size)
    }
    risk_ids = {
        row["post_id"] for row in none_rows
        if row["ai_confidence"] in {"low", "medium"}
        or bool(row["retrieval_policy_ids"].strip())
    }
    selected = [
        row for row in none_rows if row["post_id"] in random_ids | risk_ids
    ]
    return selected, random_ids, risk_ids


def duplicate_label_conflicts(
    rows: list[dict[str, str]],
) -> list[list[dict[str, str]]]:
    by_text: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        by_text[row["analysis_text"]].append(row)
    return [
        group for group in by_text.values()
        if len(group) > 1
        and len({row["human_policy_labels"] for row in group}) > 1
    ]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path,
        default=root / "data" / "private" / "post_review_working.csv",
    )
    parser.add_argument(
        "--output", type=Path,
        default=root / "data" / "private" / "post_review_none_audit.csv",
    )
    parser.add_argument("--sample-size", type=int, default=50)
    parser.add_argument("--seed", type=int, default=20260905)
    parser.add_argument("--audited-by", default="codex-gpt-5-second-pass")
    parser.add_argument("--audited-at", default="2026-09-05")
    args = parser.parse_args()
    try:
        with args.input.open(encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        conflicts = duplicate_label_conflicts(rows)
        if conflicts:
            raise ValueError(
                f"inconsistent labels in {len(conflicts)} exact-duplicate groups"
            )
        selected, random_ids, risk_ids = select_audit_rows(
            rows, args.sample_size, args.seed
        )
        output_rows: list[dict[str, str]] = []
        for row in selected:
            groups: list[str] = []
            if row["post_id"] in random_ids:
                groups.append("random_none")
            if row["retrieval_policy_ids"].strip():
                groups.append("risk_retrieval_none")
            if row["ai_confidence"] in {"low", "medium"}:
                groups.append("risk_low_or_medium")
            output_rows.append({
                "audit_groups": "|".join(groups),
                "sample_seed": str(args.seed),
                "post_id": row["post_id"],
                "candidate_key": row["candidate_key"],
                "x_handle": row["x_handle"],
                "post_url": row["post_url"],
                "analysis_text": row["analysis_text"],
                "review_stratum": row["review_stratum"],
                "ai_confidence": row["ai_confidence"],
                "retrieval_policy_ids": row["retrieval_policy_ids"],
                "human_policy_labels": row["human_policy_labels"],
                "audit_verdict": "upheld_none",
                "audit_policy_labels": "none",
                "audit_reason": (
                    "本文を再確認し、対象23政策の具体策・方向・分野言及を"
                    "確認しなかった。"
                ),
                "audited_by": args.audited_by,
                "audited_at": args.audited_at,
            })
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=OUTPUT_FIELDS)
            writer.writeheader()
            writer.writerows(output_rows)
        args.output.chmod(0o600)
    except (OSError, KeyError, ValueError) as exc:
        print(f"監査標本の作成に失敗しました: {exc}", file=sys.stderr)
        return 1
    print(
        f"wrote {len(output_rows)} audit rows; random={len(random_ids)}, "
        f"risk={len(risk_ids)}, overlap={len(random_ids & risk_ids)}; "
        f"duplicate_label_conflicts=0; output={args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
