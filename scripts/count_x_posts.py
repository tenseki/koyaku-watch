#!/usr/bin/env python3
"""公式X掲載候補者の対象期間投稿数をFull-archive Countsで調べる。"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from check_x_api import ENV_NAME, XApiError, api_get, load_local_env
except ImportError:
    from scripts.check_x_api import ENV_NAME, XApiError, api_get, load_local_env


OUTPUT_FIELDS = [
    "candidate_key",
    "name",
    "x_handle",
    "total_post_count",
    "counts_by_day_json",
    "start_time",
    "end_time_exclusive",
    "retrieved_at",
]


def load_scope(config_path: Path, candidate_file: Path) -> tuple[list[dict[str, str]], str, str]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    target = config["target"]
    with candidate_file.open(encoding="utf-8", newline="") as file:
        candidates = [row for row in csv.DictReader(file) if row.get("x_handle", "").strip()]
    return candidates, target["start_time_utc"], target["end_time_utc_exclusive"]


def count_posts(bearer_token: str, handle: str, start_time: str, end_time: str) -> dict:
    payload = api_get(
        "/tweets/counts/all",
        bearer_token,
        {
            "query": f"from:{handle}",
            "start_time": start_time,
            "end_time": end_time,
            "granularity": "day",
        },
    )
    day_counts = [
        {
            "start": item["start"],
            "end": item["end"],
            "post_count": int(item["tweet_count"]),
        }
        for item in payload.get("data", [])
    ]
    total = int(payload.get("meta", {}).get("total_tweet_count", sum(
        item["post_count"] for item in day_counts
    )))
    return {"total": total, "days": day_counts}


def read_existing(path: Path) -> dict[str, dict[str, str]]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8", newline="") as file:
        return {row["candidate_key"]: row for row in csv.DictReader(file)}


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    temporary.chmod(0o600)
    temporary.replace(path)
    path.chmod(0o600)


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--analysis-config",
        type=Path,
        default=root / "config" / "analysis_mvp_2026.json",
    )
    parser.add_argument(
        "--candidate-file",
        type=Path,
        default=root / "data" / "candidate_x_accounts_2026.csv",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "data" / "private" / "all_candidate_post_counts.csv",
    )
    parser.add_argument("--candidate-key", action="append", dest="candidate_keys")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--request-interval", type=float, default=1.1)
    parser.add_argument("--env-file", type=Path, default=root / ".env")
    parser.add_argument("--execute", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        candidates, start_time, end_time = load_scope(
            args.analysis_config, args.candidate_file
        )
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"件数調査の設定を読み込めません: {exc}", file=sys.stderr)
        return 2

    if args.candidate_keys:
        requested = set(args.candidate_keys)
        candidates = [row for row in candidates if row["candidate_key"] in requested]
        found = {row["candidate_key"] for row in candidates}
        if found != requested:
            print(f"候補者が見つかりません: {sorted(requested - found)}", file=sys.stderr)
            return 2
    existing = read_existing(args.output)
    pending = [row for row in candidates if row["candidate_key"] not in existing]
    if args.limit is not None:
        if args.limit < 1:
            print("--limit は1以上にしてください。", file=sys.stderr)
            return 2
        pending = pending[:args.limit]

    print(f"候補者総数: {len(candidates)}")
    print(f"調査済み: {len(candidates) - len([r for r in candidates if r['candidate_key'] not in existing])}")
    print(f"今回の調査対象: {len(pending)}")
    print(f"期間(UTC): {start_time} 以上、{end_time} 未満")
    if not args.execute:
        print("プレビューのみ: Counts APIは呼び出していません。")
        return 0

    load_local_env(args.env_file)
    bearer_token = os.environ.get(ENV_NAME, "").strip()
    if not bearer_token:
        print(f"{ENV_NAME} が未設定です。", file=sys.stderr)
        return 2

    ordered_keys = [row["candidate_key"] for row in candidates]
    for index, candidate in enumerate(pending, start=1):
        if index > 1:
            time.sleep(args.request_interval)
        handle = candidate["x_handle"].strip().lstrip("@")
        try:
            result = count_posts(bearer_token, handle, start_time, end_time)
        except XApiError as exc:
            print(f"件数調査を停止しました ({candidate['candidate_key']}): {exc}", file=sys.stderr)
            return 1
        existing[candidate["candidate_key"]] = {
            "candidate_key": candidate["candidate_key"],
            "name": candidate["name"],
            "x_handle": handle,
            "total_post_count": str(result["total"]),
            "counts_by_day_json": json.dumps(result["days"], ensure_ascii=False),
            "start_time": start_time,
            "end_time_exclusive": end_time,
            "retrieved_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        rows = [existing[key] for key in ordered_keys if key in existing]
        write_rows(args.output, rows)
        if index == 1 or index % 25 == 0 or index == len(pending):
            print(f"進捗: {index}/{len(pending)}（@{handle}: {result['total']}件）")

    print(f"件数調査完了: {len(pending)}名 -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
