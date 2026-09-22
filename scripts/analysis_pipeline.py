#!/usr/bin/env python3
"""Policy-to-post similarity and labeling sample helpers."""

from __future__ import annotations

import csv
import hashlib
import math
import random
from pathlib import Path
from typing import Iterable, Protocol, Sequence

import numpy as np


PROCESSED_REQUIRED_FIELDS = {
    "post_id", "candidate_key", "x_handle", "created_at", "post_type",
    "post_url", "analysis_text", "is_analysis_target",
}
SIMILARITY_FIELDS = [
    "policy_set", "policy_id", "policy_title", "post_id", "candidate_key",
    "x_handle", "created_at", "post_type", "post_url", "analysis_text",
    "similarity", "rank", "keyword_matches",
]
LABELING_FIELDS = [
    "policy_set", "policy_id", "policy_title", "analysis_text", "post_id",
    "candidate_key", "x_handle", "created_at", "post_type", "post_url",
    "similarity", "rank", "keyword_matches",
    "selection_reason",
    "mention_level",
    "evidence_text",
    "annotator",
    "labeled_at",
    "judgment_reason_code",
    "judgment_reason",
]


class TextEncoder(Protocol):
    def encode(self, texts: Sequence[str]) -> np.ndarray: ...


def read_processed_posts(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        fields = set(reader.fieldnames or [])
        missing = PROCESSED_REQUIRED_FIELDS.difference(fields)
        if missing:
            raise ValueError(f"processed post fields missing: {', '.join(sorted(missing))}")
        rows = list(reader)
    seen: set[str] = set()
    included: list[dict[str, str]] = []
    for row in rows:
        post_id = row["post_id"].strip()
        if post_id in seen:
            raise ValueError(f"duplicate post_id: {post_id}")
        seen.add(post_id)
        if row["is_analysis_target"].strip().lower() == "true":
            if not row["analysis_text"].strip():
                raise ValueError(f"analysis target has empty analysis_text: {post_id}")
            included.append(row)
    if not included:
        raise ValueError("processed post CSV has no analysis targets")
    return included


def build_policy_text(row: dict[str, str], fields: Sequence[str]) -> str:
    missing = [field for field in fields if field not in row]
    if missing:
        raise ValueError(f"comparison fields missing: {', '.join(missing)}")
    return " ".join(row[field].strip() for field in fields if row[field].strip())


def split_keywords(value: str) -> list[str]:
    return [keyword.strip() for keyword in value.split("|") if keyword.strip()]


def find_keyword_matches(text: str, keywords: Sequence[str]) -> list[str]:
    folded = text.casefold()
    return [keyword for keyword in keywords if keyword.casefold() in folded]


def _normalized(vectors: np.ndarray) -> np.ndarray:
    array = np.asarray(vectors, dtype=float)
    if array.ndim != 2:
        raise ValueError("encoder output must be a two-dimensional array")
    norms = np.linalg.norm(array, axis=1, keepdims=True)
    if np.any(norms == 0):
        raise ValueError("encoder returned a zero-length vector")
    return array / norms


def calculate_similarity_rows(
    policy_rows: Sequence[dict[str, str]],
    posts: Sequence[dict[str, str]],
    policy_set: str,
    comparison_fields: Sequence[str],
    query_prefix: str,
    document_prefix: str,
    encoder: TextEncoder,
) -> list[dict[str, str]]:
    policy_inputs = [
        query_prefix + build_policy_text(row, comparison_fields)
        for row in policy_rows
    ]
    post_inputs = [document_prefix + row["analysis_text"] for row in posts]
    policy_vectors = _normalized(encoder.encode(policy_inputs))
    post_vectors = _normalized(encoder.encode(post_inputs))
    scores = policy_vectors @ post_vectors.T
    output: list[dict[str, str]] = []
    for policy_index, policy in enumerate(policy_rows):
        ranked = sorted(
            range(len(posts)),
            key=lambda index: (-scores[policy_index, index], posts[index]["post_id"]),
        )
        keywords = split_keywords(policy.get("keywords", ""))
        for rank, post_index in enumerate(ranked, start=1):
            post = posts[post_index]
            matches = find_keyword_matches(post["analysis_text"], keywords)
            output.append({
                "policy_set": policy_set,
                "policy_id": policy["policy_id"],
                "policy_title": policy["title"],
                "post_id": post["post_id"],
                "candidate_key": post["candidate_key"],
                "x_handle": post["x_handle"],
                "created_at": post["created_at"],
                "post_type": post["post_type"],
                "post_url": post["post_url"],
                "analysis_text": post["analysis_text"],
                "similarity": f"{scores[policy_index, post_index]:.8f}",
                "rank": str(rank),
                "keyword_matches": "|".join(matches),
            })
    return output


def _stable_random(seed: int, policy_id: str, stratum: str) -> random.Random:
    digest = hashlib.sha256(f"{seed}:{policy_id}:{stratum}".encode()).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _diverse_sample(
    rows: Sequence[dict[str, str]], size: int, rng: random.Random
) -> list[dict[str, str]]:
    groups: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault(row["candidate_key"], []).append(row)
    candidates = sorted(groups)
    rng.shuffle(candidates)
    for group in groups.values():
        rng.shuffle(group)
    selected: list[dict[str, str]] = []
    while candidates and len(selected) < size:
        remaining_candidates: list[str] = []
        for candidate in candidates:
            group = groups[candidate]
            if group and len(selected) < size:
                selected.append(group.pop())
            if group:
                remaining_candidates.append(candidate)
        candidates = remaining_candidates
    return selected


def select_labeling_candidates(
    similarity_rows: Sequence[dict[str, str]],
    top_k: int,
    middle_sample_size: int,
    low_sample_size: int,
    random_seed: int,
    middle_start: float = 0.4,
    middle_end: float = 0.6,
    low_start: float = 0.8,
) -> list[dict[str, str]]:
    if not (0 <= middle_start < middle_end <= low_start <= 1):
        raise ValueError("invalid sampling percentile boundaries")
    by_policy: dict[str, list[dict[str, str]]] = {}
    policy_order: list[str] = []
    for row in similarity_rows:
        policy_id = row["policy_id"]
        if policy_id not in by_policy:
            policy_order.append(policy_id)
            by_policy[policy_id] = []
        by_policy[policy_id].append(row)
    output: list[dict[str, str]] = []
    for policy_id in policy_order:
        rows = sorted(by_policy[policy_id], key=lambda row: int(row["rank"]))
        reasons: dict[str, set[str]] = {}
        selected_rows: dict[str, dict[str, str]] = {}

        def add(row: dict[str, str], selection_reason: str) -> None:
            key = row["post_id"]
            selected_rows[key] = row
            reasons.setdefault(key, set()).add(selection_reason)

        for row in rows[:top_k]:
            add(row, "similarity_top")
        for row in rows:
            if row["keyword_matches"]:
                add(row, "keyword_match")
        count = len(rows)
        middle_pool = rows[math.floor(count * middle_start):math.ceil(count * middle_end)]
        low_pool = rows[math.floor(count * low_start):]
        middle_pool = [row for row in middle_pool if row["post_id"] not in selected_rows]
        low_pool = [row for row in low_pool if row["post_id"] not in selected_rows]
        for row in _diverse_sample(
            middle_pool,
            middle_sample_size,
            _stable_random(random_seed, policy_id, "middle"),
        ):
            add(row, "random_middle")
        available_low = [row for row in low_pool if row["post_id"] not in selected_rows]
        for row in _diverse_sample(
            available_low,
            low_sample_size,
            _stable_random(random_seed, policy_id, "low"),
        ):
            add(row, "random_low")
        for row in sorted(selected_rows.values(), key=lambda item: int(item["rank"])):
            output.append({
                **row,
                "selection_reason": "|".join(sorted(reasons[row["post_id"]])),
                "mention_level": "",
                "evidence_text": "",
                "annotator": "",
                "labeled_at": "",
                "judgment_reason_code": "",
                "judgment_reason": "",
            })
    return output


def write_csv(path: Path, fields: Sequence[str], rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in rows)
    path.chmod(0o600)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
