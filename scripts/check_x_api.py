#!/usr/bin/env python3
"""X APIの認証と、必要に応じて公開投稿1件の取得を確認する。"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


API_BASE_URL = "https://api.x.com/2"
ENV_NAME = "X_API_BEARER_TOKEN"


class XApiError(RuntimeError):
    """X APIの呼び出しに失敗した。"""


def load_local_env(path: Path) -> None:
    """単純なKEY=VALUE形式の.envを、既存環境変数を上書きせず読み込む。"""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value[:1] == value[-1:] and value[:1] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def api_get(path: str, bearer_token: str, params: dict[str, str] | None = None) -> dict:
    query = urllib.parse.urlencode(params or {})
    url = f"{API_BASE_URL}{path}"
    if query:
        url = f"{url}?{query}"

    request = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {bearer_token}",
            "User-Agent": "koyaku-watch-api-check/0.1",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.dumps(json.loads(body), ensure_ascii=False)
        except json.JSONDecodeError:
            detail = body[:500]
        raise XApiError(f"X API returned HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise XApiError(f"X APIに接続できません: {exc.reason}") from exc


def lookup_user(username: str, bearer_token: str) -> dict:
    encoded_username = urllib.parse.quote(username.lstrip("@"), safe="")
    payload = api_get(
        f"/users/by/username/{encoded_username}",
        bearer_token,
        {"user.fields": "id,name,username,protected,pinned_tweet_id"},
    )
    if "data" not in payload:
        raise XApiError(f"ユーザー情報がありません: {json.dumps(payload, ensure_ascii=False)}")
    return payload["data"]


def lookup_post(post_id: str, bearer_token: str) -> dict:
    encoded_post_id = urllib.parse.quote(post_id, safe="")
    payload = api_get(
        f"/tweets/{encoded_post_id}",
        bearer_token,
        {"tweet.fields": "author_id,created_at"},
    )
    if "data" not in payload:
        raise XApiError(f"投稿情報がありません: {json.dumps(payload, ensure_ascii=False)}")
    return payload["data"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--username",
        default="XDevelopers",
        help="認証確認に使う公開Xアカウント（既定: XDevelopers）",
    )
    parser.add_argument(
        "--fetch-pinned-post",
        action="store_true",
        help="対象アカウントに固定投稿があれば、その1件も取得する",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(__file__).resolve().parents[1] / ".env",
        help="Bearer Tokenを読む.envファイル",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_local_env(args.env_file)
    bearer_token = os.environ.get(ENV_NAME, "").strip()
    if not bearer_token:
        print(
            f"{ENV_NAME} が未設定です。.envの等号の右側にBearer Tokenを貼り付けてください。",
            file=sys.stderr,
        )
        return 2

    try:
        user = lookup_user(args.username, bearer_token)
        protected = "非公開" if user.get("protected") else "公開"
        print(
            "認証成功: "
            f"@{user['username']} / {user['name']} / user_id={user['id']} / {protected}"
        )

        if args.fetch_pinned_post:
            post_id = user.get("pinned_tweet_id")
            if not post_id:
                print("このアカウントには固定投稿がないため、投稿取得は行いませんでした。")
                return 0
            post = lookup_post(post_id, bearer_token)
            print(f"固定投稿1件を取得: https://x.com/{user['username']}/status/{post['id']}")
            print(f"投稿日時: {post.get('created_at', '不明')}")
            print(f"本文: {post.get('text', '')}")
    except XApiError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
