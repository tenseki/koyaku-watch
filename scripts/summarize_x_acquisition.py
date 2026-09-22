#!/usr/bin/env python3
"""MVP対象候補者の取得完了状況を、本文を出力せず集計する。"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--analysis-config",
        type=Path,
        default=root / "config" / "analysis_mvp_2026.json",
    )
    parser.add_argument("--input-dir", type=Path, default=root / "data" / "private")
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "data" / "private" / "acquisition_summary.json",
    )
    return parser.parse_args()


def load_candidates(config_path: Path) -> list[dict[str, str]]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    target = config["target"]
    candidate_path = Path(target["candidate_file"])
    if not candidate_path.is_absolute():
        candidate_path = (config_path.parent / candidate_path).resolve()
    with candidate_path.open(encoding="utf-8", newline="") as file:
        candidates = list(csv.DictReader(file))
    expected_count = int(target["candidate_count"])
    if len(candidates) != expected_count:
        raise ValueError(
            f"candidate count mismatch: expected {expected_count}, found {len(candidates)}"
        )
    return candidates


def summarize_candidate(input_dir: Path, candidate: dict[str, str]) -> dict:
    candidate_key = candidate["candidate_key"]
    metadata_path = input_dir / f"{candidate_key}_posts.metadata.json"
    processed_path = input_dir / f"{candidate_key}_posts.processed.csv"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    with processed_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    if len(rows) != int(metadata["retrieved_count"]):
        raise ValueError(f"row count mismatch: {candidate_key}")
    included = sum(row.get("is_analysis_target") == "true" for row in rows)
    post_types = Counter(row.get("post_type", "") for row in rows)
    exclusion_reasons = Counter(
        row.get("exclusion_reason", "")
        for row in rows
        if row.get("exclusion_reason", "")
    )
    return {
        "candidate_key": candidate_key,
        "name": candidate["name"],
        "x_handle": candidate["x_handle"],
        "retrieved_count": len(rows),
        "analysis_target_count": included,
        "excluded_count": len(rows) - included,
        "post_types": dict(sorted(post_types.items())),
        "exclusion_reasons": dict(sorted(exclusion_reasons.items())),
        "pages_fetched": metadata["pages_fetched"],
        "duplicates_ignored": metadata["duplicates_ignored"],
        "complete": not metadata["more_results_available"],
        "retrieved_at": metadata["retrieved_at"],
        "output_sha256": metadata["output_sha256"],
    }


def main() -> int:
    args = parse_args()
    try:
        candidates = load_candidates(args.analysis_config)
        summaries = [summarize_candidate(args.input_dir, candidate) for candidate in candidates]
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"取得集計に失敗しました: {exc}", file=sys.stderr)
        return 1

    result = {
        "schema_version": "1.0",
        "candidate_count": len(summaries),
        "all_complete": all(item["complete"] for item in summaries),
        "retrieved_total": sum(item["retrieved_count"] for item in summaries),
        "analysis_target_total": sum(item["analysis_target_count"] for item in summaries),
        "excluded_total": sum(item["excluded_count"] for item in summaries),
        "candidates": summaries,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    args.output.chmod(0o600)
    print(
        f"取得集計: {result['candidate_count']}名 / {result['retrieved_total']}投稿 / "
        f"分析対象{result['analysis_target_total']} / 除外{result['excluded_total']} / "
        f"全件完了={result['all_complete']}"
    )
    return 0 if result["all_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
