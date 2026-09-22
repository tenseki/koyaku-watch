#!/usr/bin/env python3
"""Validate a policy/post human-labeling worksheet against the analysis config."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


POSITIVE_CODES = {
    "specific_measure": "target_specific_measure",
    "policy_direction": "target_policy_direction",
    "topic_only": "target_topic_only",
}
NONE_CODES = {
    "election_call_only",
    "campaign_event_notice_only",
    "unrelated_topic",
}
UNCERTAIN_CODES = {"insufficient_context", "ambiguous_policy_mapping"}


def validate_rows(
    rows: list[dict[str, str]], config: dict, require_complete: bool = False
) -> list[str]:
    labeling = config["human_labeling"]
    label_field = labeling["field"]
    evidence_field = labeling["evidence_field"]
    reason_code_field = labeling["reason_code_field"]
    reason_field = labeling["reason_field"]
    allowed_labels = set(labeling["allowed_labels"])
    allowed_codes = set(labeling["allowed_reason_codes"])
    errors: list[str] = []
    seen: set[tuple[str, str]] = set()

    for line_number, row in enumerate(rows, start=2):
        key = (row.get("policy_id", "").strip(), row.get("post_id", "").strip())
        if not all(key):
            errors.append(f"line {line_number}: policy_id and post_id are required")
        elif key in seen:
            errors.append(f"line {line_number}: duplicate policy_id/post_id pair: {key}")
        seen.add(key)

        label = row.get(label_field, "").strip()
        code = row.get(reason_code_field, "").strip()
        evidence = row.get(evidence_field, "").strip()
        reason = row.get(reason_field, "").strip()
        if not label and not code:
            if require_complete:
                errors.append(f"line {line_number}: labeling is incomplete")
            continue
        if label not in allowed_labels:
            errors.append(f"line {line_number}: invalid {label_field}: {label}")
        if code not in allowed_codes:
            errors.append(f"line {line_number}: invalid {reason_code_field}: {code}")
        if label in POSITIVE_CODES:
            if code != POSITIVE_CODES[label]:
                errors.append(
                    f"line {line_number}: {label} requires {POSITIVE_CODES[label]}"
                )
            if not evidence:
                errors.append(f"line {line_number}: {label} requires {evidence_field}")
        elif label == "none" and code not in NONE_CODES | {"other"}:
            errors.append(f"line {line_number}: none is incompatible with {code}")
        elif label == "uncertain" and code not in UNCERTAIN_CODES | {"other"}:
            errors.append(f"line {line_number}: uncertain is incompatible with {code}")
        if code == "other" and not reason:
            errors.append(f"line {line_number}: other requires {reason_field}")
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--analysis-config",
        type=Path,
        default=root / "config" / "analysis_mvp_2026.json",
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()

    try:
        config = json.loads(args.analysis_config.read_text(encoding="utf-8"))
        with args.input.open(encoding="utf-8", newline="") as file:
            rows = list(csv.DictReader(file))
        errors = validate_rows(rows, config, args.require_complete)
        label_field = config["human_labeling"]["field"]
    except (OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"ラベリング検証に失敗しました: {exc}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        print(f"ラベリング検証: {len(errors)}件のエラー", file=sys.stderr)
        return 1
    completed = sum(bool(row.get(label_field, "").strip()) for row in rows)
    print(f"ラベリング検証: {len(rows)}行中{completed}行入力済み、エラー0件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
