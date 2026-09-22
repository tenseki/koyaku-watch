#!/usr/bin/env python3
"""候補者の投稿を費用見積もり・再開機能付きで取得し、前処理する。"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

try:
    from fetch_x_posts import POST_READ_UNIT_USD, load_plan
except ImportError:
    from scripts.fetch_x_posts import POST_READ_UNIT_USD, load_plan


DEFAULT_CANDIDATE_KEYS = [
    "hayashi-yoshimasa",
    "hiraguchi-hiroshi",
    "motegi-toshimitsu",
    "matsumoto-yohei",
]


def load_candidate_keys(config_path: Path) -> list[str]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    target = config["target"]
    candidate_file = Path(target["candidate_file"])
    if not candidate_file.is_absolute():
        candidate_file = (config_path.parent / candidate_file).resolve()
    with candidate_file.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    expected_count = int(target["candidate_count"])
    keys = [row.get("candidate_key", "").strip() for row in rows]
    if len(keys) != expected_count or len(set(keys)) != expected_count or "" in keys:
        raise ValueError(
            f"candidate scope mismatch: expected {expected_count}, found {len(keys)}"
        )
    return keys


def load_expected_counts(path: Path) -> dict[str, int]:
    with path.open(encoding="utf-8", newline="") as file:
        return {
            row["candidate_key"].strip(): int(row["total_post_count"])
            for row in csv.DictReader(file)
        }


def completed_output(output: Path, metadata_path: Path) -> bool:
    """Return true only for a complete file whose recorded hash still matches."""
    if not output.exists() or not metadata_path.exists():
        return False
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("more_results_available"):
            return False
        if metadata.get("output_sha256") != hashlib.sha256(output.read_bytes()).hexdigest():
            return False
        with output.open(encoding="utf-8", newline="") as file:
            row_count = sum(1 for _ in csv.DictReader(file))
        return row_count == int(metadata["retrieved_count"])
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return False


def parse_args() -> argparse.Namespace:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidate-key",
        action="append",
        dest="candidate_keys",
        help="取得対象。複数回指定可（省略時は第1バッチの4名）",
    )
    parser.add_argument(
        "--all-candidates",
        action="store_true",
        help="設定ファイルに記載された全候補者を対象にする",
    )
    parser.add_argument(
        "--analysis-config",
        type=Path,
        default=root / "config" / "analysis_mvp_2026.json",
    )
    parser.add_argument("--page-size", type=int, default=100)
    parser.add_argument("--max-pages", type=int, default=1)
    parser.add_argument(
        "--candidate-interval",
        type=float,
        default=1.1,
        help="候補者ごとの取得開始間隔（秒）。15分上限を考慮する場合は5.2秒以上",
    )
    parser.add_argument("--output-dir", type=Path, default=root / "data" / "private")
    parser.add_argument(
        "--counts-file",
        type=Path,
        default=root / "data" / "private" / "all_candidate_post_counts.csv",
        help="取得済み件数表（実費見積もりと取得後照合に使用）",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="ハッシュ検証できた取得済み候補者を飛ばして再開する",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="実際に課金対象のAPIリクエストと前処理を行う",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.all_candidates and args.candidate_keys:
        print("--all-candidates と --candidate-key は同時指定できません。", file=sys.stderr)
        return 2
    try:
        candidate_keys = (
            load_candidate_keys(args.analysis_config)
            if args.all_candidates
            else args.candidate_keys or DEFAULT_CANDIDATE_KEYS
        )
        expected_counts = load_expected_counts(args.counts_file)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        print(f"取得対象または件数表を読み込めません: {exc}", file=sys.stderr)
        return 2
    if len(candidate_keys) != len(set(candidate_keys)):
        print("candidate_keyが重複しています。", file=sys.stderr)
        return 2
    if (
        not 10 <= args.page_size <= 500
        or args.max_pages < 1
        or args.candidate_interval < 0
    ):
        print("page-sizeは10〜500、max-pagesは1以上にしてください。", file=sys.stderr)
        return 2

    plans = []
    try:
        for candidate_key in candidate_keys:
            plans.append(load_plan(args.analysis_config, candidate_key))
    except (OSError, KeyError, ValueError) as exc:
        print(f"取得計画を読み込めません: {exc}", file=sys.stderr)
        return 2

    selected_plans = []
    skipped_plans = []
    for plan in plans:
        key = plan["candidate"]["candidate_key"]
        output = args.output_dir / f"{key}_posts.csv"
        metadata = args.output_dir / f"{key}_posts.metadata.json"
        if args.resume and completed_output(output, metadata):
            skipped_plans.append(plan)
        else:
            selected_plans.append(plan)

    missing_counts = [
        plan["candidate"]["candidate_key"]
        for plan in selected_plans
        if plan["candidate"]["candidate_key"] not in expected_counts
    ]
    if missing_counts:
        print(f"件数表に候補者がありません: {missing_counts}", file=sys.stderr)
        return 2

    per_candidate_max = args.page_size * args.max_pages
    total_max = per_candidate_max * len(selected_plans)
    maximum_cost = total_max * POST_READ_UNIT_USD
    expected_posts = sum(
        expected_counts[plan["candidate"]["candidate_key"]]
        for plan in selected_plans
    )
    expected_cost = expected_posts * POST_READ_UNIT_USD
    print(f"設定上の候補者: {len(plans)}名")
    print(f"検証済み・スキップ: {len(skipped_plans)}名")
    print(f"今回の取得対象: {len(selected_plans)}名")
    print(f"候補者ごとの上限: {per_candidate_max}投稿")
    print(f"全体上限: {total_max}投稿")
    print(f"件数表による取得見込み: {expected_posts}投稿 / ${expected_cost:.3f}")
    print(f"設定上の費用上限: ${maximum_cost:.2f}")
    if not args.execute:
        print("プレビューのみ: APIリクエストは行っていません。")
        return 0

    root = Path(__file__).resolve().parents[1]
    fetch_script = root / "scripts" / "fetch_x_posts.py"
    preprocess_script = root / "scripts" / "preprocess_posts.py"
    args.output_dir.mkdir(parents=True, exist_ok=True)

    mismatches = []
    for index, plan in enumerate(selected_plans):
        if index:
            time.sleep(args.candidate_interval)
        candidate_key = plan["candidate"]["candidate_key"]
        output = args.output_dir / f"{candidate_key}_posts.csv"
        metadata = args.output_dir / f"{candidate_key}_posts.metadata.json"
        processed = args.output_dir / f"{candidate_key}_posts.processed.csv"
        fetch_command = [
            sys.executable,
            str(fetch_script),
            "--analysis-config",
            str(args.analysis_config),
            "--candidate-key",
            candidate_key,
            "--page-size",
            str(args.page_size),
            "--max-pages",
            str(args.max_pages),
            "--output",
            str(output),
            "--metadata",
            str(metadata),
            "--execute",
        ]
        result = subprocess.run(fetch_command, check=False)
        if result.returncode:
            print(f"取得を停止しました: {candidate_key}", file=sys.stderr)
            return result.returncode

        metadata_payload = json.loads(metadata.read_text(encoding="utf-8"))
        actual_count = int(metadata_payload["retrieved_count"])
        expected_count = expected_counts[candidate_key]
        if actual_count != expected_count:
            mismatches.append((candidate_key, expected_count, actual_count))
            print(
                f"注意: 件数調査との差 {candidate_key}: "
                f"件数表={expected_count}, 取得={actual_count}",
                file=sys.stderr,
            )
        if metadata_payload.get("more_results_available"):
            print(f"取得を停止しました（未取得ページあり）: {candidate_key}", file=sys.stderr)
            return 1

        preprocess_command = [
            sys.executable,
            str(preprocess_script),
            "--analysis-config",
            str(args.analysis_config),
            "--input",
            str(output),
            "--output",
            str(processed),
        ]
        result = subprocess.run(preprocess_command, check=False)
        if result.returncode:
            print(f"前処理を停止しました: {candidate_key}", file=sys.stderr)
            return result.returncode

    print(f"バッチ完了: {len(selected_plans)}名（スキップ {len(skipped_plans)}名）")
    if mismatches:
        print(f"件数差あり: {len(mismatches)}名（取得時点の実データを保存済み）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
