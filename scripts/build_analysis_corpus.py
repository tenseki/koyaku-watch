#!/usr/bin/env python3
"""Combine per-candidate processed post files into one validated MVP corpus."""

from __future__ import annotations

import argparse
import csv
import json
import sys
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
        default=root / "data" / "private" / "mvp_posts.processed.csv",
    )
    return parser.parse_args()


def load_candidate_keys(config_path: Path) -> list[str]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    target = config["target"]
    candidate_path = Path(target["candidate_file"])
    if not candidate_path.is_absolute():
        candidate_path = (config_path.parent / candidate_path).resolve()
    with candidate_path.open(encoding="utf-8", newline="") as file:
        keys = [row["candidate_key"] for row in csv.DictReader(file)]
    expected = int(target["candidate_count"])
    if len(keys) != expected:
        raise ValueError(
            f"candidate count mismatch: expected {expected}, found {len(keys)}"
        )
    if len(keys) != len(set(keys)):
        raise ValueError("candidate list contains duplicate candidate_key values")
    return keys


def build_corpus(
    input_dir: Path, candidate_keys: list[str]
) -> tuple[list[str], list[dict[str, str]]]:
    fieldnames: list[str] | None = None
    rows: list[dict[str, str]] = []
    seen_post_ids: set[str] = set()
    for candidate_key in candidate_keys:
        path = input_dir / f"{candidate_key}_posts.processed.csv"
        with path.open(encoding="utf-8", newline="") as file:
            reader = csv.DictReader(file)
            current_fields = list(reader.fieldnames or [])
            if not current_fields:
                raise ValueError(f"processed CSV has no header: {path}")
            if fieldnames is None:
                fieldnames = current_fields
            elif current_fields != fieldnames:
                raise ValueError(f"processed CSV fields differ: {path}")
            for row in reader:
                if row.get("candidate_key") != candidate_key:
                    raise ValueError(
                        f"candidate_key mismatch in {path}: {row.get('candidate_key', '')}"
                    )
                post_id = row.get("post_id", "").strip()
                if not post_id:
                    raise ValueError(f"empty post_id in {path}")
                if post_id in seen_post_ids:
                    raise ValueError(f"duplicate post_id across corpus: {post_id}")
                seen_post_ids.add(post_id)
                rows.append(row)
    if fieldnames is None:
        raise ValueError("no processed post files were loaded")
    return fieldnames, rows


def write_corpus(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    path.chmod(0o600)


def main() -> int:
    args = parse_args()
    try:
        candidate_keys = load_candidate_keys(args.analysis_config)
        fieldnames, rows = build_corpus(args.input_dir, candidate_keys)
        write_corpus(args.output, fieldnames, rows)
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"分析コーパスの作成に失敗しました: {exc}", file=sys.stderr)
        return 1
    included = sum(row.get("is_analysis_target") == "true" for row in rows)
    print(
        f"wrote {len(rows)} posts for {len(candidate_keys)} candidates to {args.output} "
        f"({included} included, {len(rows) - included} excluded)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
