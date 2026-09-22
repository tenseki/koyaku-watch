#!/usr/bin/env python3
"""Validate and preprocess canonical post rows without depending on X APIs."""

from __future__ import annotations

import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable


INPUT_FIELDS = [
    "post_id", "candidate_key", "author_id", "x_handle", "created_at",
    "post_type", "raw_text", "post_url", "has_media", "retrieved_at",
]
OUTPUT_FIELDS = [*INPUT_FIELDS, "analysis_text", "is_analysis_target", "exclusion_reason"]
POST_TYPES = {"post", "reply", "quote", "repost"}

URL_PATTERN = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
MENTION_PATTERN = re.compile(r"(?<![\w@])@[A-Za-z0-9_]{1,15}\b")
WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Apply the documented MVP text preprocessing rules."""
    without_urls = URL_PATTERN.sub(" ", text)
    without_mentions = MENTION_PATTERN.sub(" ", without_urls)
    return WHITESPACE_PATTERN.sub(" ", without_mentions).strip()


def preprocess_row(row: dict[str, str]) -> dict[str, str]:
    missing = [field for field in INPUT_FIELDS if field not in row]
    if missing:
        raise ValueError(f"post fields missing: {', '.join(missing)}")
    post_id = row["post_id"].strip()
    if not post_id:
        raise ValueError("post_id must not be empty")
    post_type = row["post_type"].strip().lower()
    if post_type not in POST_TYPES:
        raise ValueError(f"unknown post_type for {post_id}: {post_type}")
    analysis_text = normalize_text(row["raw_text"])
    exclusion_reason = ""
    if post_type == "repost":
        exclusion_reason = "simple_repost"
    elif not analysis_text:
        exclusion_reason = "empty_after_preprocessing"
    return {
        **{field: row.get(field, "") for field in INPUT_FIELDS},
        "post_type": post_type,
        "analysis_text": analysis_text,
        "is_analysis_target": "false" if exclusion_reason else "true",
        "exclusion_reason": exclusion_reason,
    }


def preprocess_rows(rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    seen_post_ids: set[str] = set()
    for row in rows:
        processed = preprocess_row(row)
        post_id = processed["post_id"]
        if post_id in seen_post_ids:
            raise ValueError(f"duplicate post_id: {post_id}")
        seen_post_ids.add(post_id)
        output.append(processed)
    return output


def validate_target_scope(
    rows: Iterable[dict[str, str]],
    candidate_keys: set[str],
    start_time: datetime,
    end_time_exclusive: datetime,
) -> None:
    if start_time.tzinfo is None or end_time_exclusive.tzinfo is None:
        raise ValueError("target time boundaries must include a timezone")
    for row in rows:
        post_id = row.get("post_id", "").strip() or "<unknown>"
        candidate_key = row.get("candidate_key", "").strip()
        if candidate_key not in candidate_keys:
            raise ValueError(f"candidate_key outside target scope for {post_id}: {candidate_key}")
        try:
            created_at = datetime.fromisoformat(row.get("created_at", "").replace("Z", "+00:00"))
        except ValueError as error:
            raise ValueError(f"invalid created_at for {post_id}") from error
        if created_at.tzinfo is None:
            raise ValueError(f"created_at must include a timezone for {post_id}")
        if not start_time <= created_at < end_time_exclusive:
            raise ValueError(
                f"created_at outside target period for {post_id}: "
                f"{created_at.isoformat()}"
            )


def load_target_scope(analysis_config_path: Path) -> tuple[set[str], datetime, datetime]:
    config = json.loads(analysis_config_path.read_text(encoding="utf-8"))
    target = config["target"]
    candidate_path = Path(target["candidate_file"])
    if not candidate_path.is_absolute():
        candidate_path = (analysis_config_path.parent / candidate_path).resolve()
    with candidate_path.open(encoding="utf-8", newline="") as file:
        candidates = list(csv.DictReader(file))
    expected_count = int(target["candidate_count"])
    if len(candidates) != expected_count:
        raise ValueError(
            f"candidate count mismatch: expected {expected_count}, found {len(candidates)}"
        )
    candidate_keys = {row["candidate_key"].strip() for row in candidates}
    if len(candidate_keys) != expected_count:
        raise ValueError("candidate file contains empty or duplicate candidate_key values")
    start = datetime.fromisoformat(target["start_time_jst"])
    end = datetime.fromisoformat(target["end_time_jst_exclusive"])
    return candidate_keys, start, end


def read_post_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        fields = reader.fieldnames or []
        missing = [field for field in INPUT_FIELDS if field not in fields]
        if missing:
            raise ValueError(f"post CSV fields missing: {', '.join(missing)}")
        return list(reader)


def write_processed_csv(path: Path, rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in OUTPUT_FIELDS} for row in rows)
    path.chmod(0o600)
