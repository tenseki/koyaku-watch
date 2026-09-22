#!/usr/bin/env python3
"""Full-archive Searchから対象候補者の投稿を標準CSVへ取得する。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from check_x_api import ENV_NAME, XApiError, api_get, load_local_env
    from post_processing import INPUT_FIELDS
except ImportError:  # testsからscriptsパッケージとして読み込む場合
    from scripts.check_x_api import ENV_NAME, XApiError, api_get, load_local_env
    from scripts.post_processing import INPUT_FIELDS


POST_READ_UNIT_USD = 0.005
TWEET_FIELDS = "author_id,created_at,referenced_tweets,attachments,note_tweet"


def load_candidate(candidate_file: Path, candidate_key: str) -> dict[str, str]:
    with candidate_file.open(encoding="utf-8", newline="") as file:
        matches = [
            row for row in csv.DictReader(file)
            if row.get("candidate_key", "").strip() == candidate_key
        ]
    if len(matches) != 1:
        raise ValueError(
            f"candidate_key must match exactly one row: {candidate_key} "
            f"(found {len(matches)})"
        )
    return matches[0]


def load_plan(config_path: Path, candidate_key: str) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    target = config["target"]
    candidate_file = Path(target["candidate_file"])
    if not candidate_file.is_absolute():
        candidate_file = (config_path.parent / candidate_file).resolve()
    candidate = load_candidate(candidate_file, candidate_key)
    return {
        "candidate": candidate,
        "start_time": target["start_time_utc"],
        "end_time": target["end_time_utc_exclusive"],
    }


def classify_post(post: dict) -> str:
    reference_types = {
        reference.get("type") for reference in post.get("referenced_tweets", [])
    }
    if "retweeted" in reference_types:
        return "repost"
    if "quoted" in reference_types:
        return "quote"
    if "replied_to" in reference_types:
        return "reply"
    return "post"


def full_post_text(post: dict) -> str:
    """Return long-form text when X supplies a note_tweet object."""
    note_tweet = post.get("note_tweet")
    if isinstance(note_tweet, dict):
        text = note_tweet.get("text")
        if isinstance(text, str) and text:
            return text
    return post.get("text", "")


def post_to_row(
    post: dict,
    candidate: dict[str, str],
    retrieved_at: str,
) -> dict[str, str]:
    handle = candidate["x_handle"].strip().lstrip("@")
    media_keys = post.get("attachments", {}).get("media_keys", [])
    return {
        "post_id": str(post["id"]),
        "candidate_key": candidate["candidate_key"],
        "author_id": str(post.get("author_id", "")),
        "x_handle": handle,
        "created_at": post.get("created_at", ""),
        "post_type": classify_post(post),
        "raw_text": full_post_text(post),
        "post_url": f"https://x.com/{handle}/status/{post['id']}",
        "has_media": "true" if media_keys else "false",
        "retrieved_at": retrieved_at,
    }


def fetch_pages(
    bearer_token: str,
    handle: str,
    start_time: str,
    end_time: str,
    page_size: int,
    max_pages: int,
    request_interval_seconds: float = 1.1,
) -> tuple[list[dict], dict]:
    posts: list[dict] = []
    seen_post_ids: set[str] = set()
    duplicates_ignored = 0
    next_token: str | None = None
    pages_fetched = 0
    for _ in range(max_pages):
        if pages_fetched:
            time.sleep(request_interval_seconds)
        params = {
            "query": f"from:{handle}",
            "start_time": start_time,
            "end_time": end_time,
            "max_results": str(page_size),
            "tweet.fields": TWEET_FIELDS,
        }
        if next_token:
            params["next_token"] = next_token
        payload = api_get("/tweets/search/all", bearer_token, params)
        pages_fetched += 1
        for post in payload.get("data", []):
            post_id = str(post.get("id", ""))
            if post_id in seen_post_ids:
                duplicates_ignored += 1
                continue
            seen_post_ids.add(post_id)
            posts.append(post)
        next_token = payload.get("meta", {}).get("next_token")
        if not next_token:
            break
    return posts, {
        "pages_fetched": pages_fetched,
        "more_results_available": bool(next_token),
        "duplicates_ignored": duplicates_ignored,
    }


def write_csv(path: Path, rows: list[dict[str, str]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=INPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    path.chmod(0o600)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--analysis-config",
        type=Path,
        default=root / "config" / "analysis_mvp_2026.json",
    )
    parser.add_argument("--candidate-key", default="takaichi-sanae")
    parser.add_argument("--page-size", type=int, default=10)
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--env-file", type=Path, default=root / ".env")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="実際に課金対象のAPIリクエストを行う",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 10 <= args.page_size <= 500:
        print("--page-size は10以上500以下にしてください。", file=sys.stderr)
        return 2
    if args.max_pages < 1:
        print("--max-pages は1以上にしてください。", file=sys.stderr)
        return 2

    try:
        plan = load_plan(args.analysis_config, args.candidate_key)
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"取得計画を読み込めません: {exc}", file=sys.stderr)
        return 2

    candidate = plan["candidate"]
    handle = candidate["x_handle"].strip().lstrip("@")
    maximum_posts = args.page_size * args.max_pages
    maximum_cost = maximum_posts * POST_READ_UNIT_USD
    print(f"候補者: {candidate['name']} (@{handle})")
    print(f"期間(UTC): {plan['start_time']} 以上、{plan['end_time']} 未満")
    print(f"取得上限: {maximum_posts}投稿 ({args.page_size}件 × {args.max_pages}ページ)")
    print(f"投稿読み取り費用の上限目安: ${maximum_cost:.3f}")

    if not args.execute:
        print("プレビューのみ: APIリクエストは行っていません。実行時は --execute を付けます。")
        return 0

    load_local_env(args.env_file)
    bearer_token = os.environ.get(ENV_NAME, "").strip()
    if not bearer_token:
        print(f"{ENV_NAME} が未設定です。", file=sys.stderr)
        return 2

    root = Path(__file__).resolve().parents[1]
    output = args.output or root / "data" / "private" / f"pilot_{args.candidate_key}_posts.csv"
    metadata_path = args.metadata or output.with_suffix(".metadata.json")
    retrieved_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    try:
        posts, pagination = fetch_pages(
            bearer_token,
            handle,
            plan["start_time"],
            plan["end_time"],
            args.page_size,
            args.max_pages,
        )
    except XApiError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    rows = [post_to_row(post, candidate, retrieved_at) for post in posts]
    digest = write_csv(output, rows)
    metadata = {
        "schema_version": "1.0",
        "endpoint": "/2/tweets/search/all",
        "authentication": "app-only bearer token",
        "query": f"from:{handle}",
        "candidate_key": candidate["candidate_key"],
        "x_handle": handle,
        "start_time": plan["start_time"],
        "end_time_exclusive": plan["end_time"],
        "page_size": args.page_size,
        "max_pages": args.max_pages,
        "retrieved_count": len(rows),
        "retrieved_at": retrieved_at,
        "pages_fetched": pagination["pages_fetched"],
        "more_results_available": pagination["more_results_available"],
        "duplicates_ignored": pagination["duplicates_ignored"],
        "cost_assumption_usd_per_post": POST_READ_UNIT_USD,
        "maximum_estimated_cost_usd": maximum_cost,
        "output_sha256": digest,
    }
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    metadata_path.chmod(0o600)
    print(f"取得完了: {len(rows)}投稿 -> {output}")
    print(f"取得ログ: {metadata_path}")
    if pagination["more_results_available"]:
        print("注意: ページ上限に達し、対象期間に未取得の投稿が残っています。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
