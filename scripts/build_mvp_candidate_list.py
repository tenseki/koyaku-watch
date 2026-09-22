#!/usr/bin/env python3
"""Build the MVP candidate list from a documented eligibility configuration."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    with args.candidates.open(encoding="utf-8", newline="") as file:
        candidate_rows = {row["candidate_key"]: row for row in csv.DictReader(file)}
    config = json.loads(args.config.read_text(encoding="utf-8"))

    output_rows = []
    for entry in config["candidates"]:
        key = entry["candidate_key"]
        if key not in candidate_rows:
            raise ValueError(f"candidate_key not found: {key}")
        row = candidate_rows[key].copy()
        if not row["official_x_url"]:
            raise ValueError(f"official X link missing: {key}")
        row.update(
            {
                "selection_name": config["selection_name"],
                "selection_priority": "1",
                "selection_reason": "解散時閣僚かつ公式候補者ページにXリンク掲載",
                "cabinet_position_at_dissolution": entry["cabinet_position"],
                "cabinet_started_at": config["cabinet_started_at"],
                "dissolution_date": config["dissolution_date"],
                "cabinet_source_url": config["cabinet_source_url"],
            }
        )
        output_rows.append(row)

    fields = [
        "candidate_key", "name", "prefecture", "constituency", "proportional_block",
        "official_x_url", "x_handle", "candidate_page_url", "selection_name",
        "selection_priority", "selection_reason", "cabinet_position_at_dissolution",
        "cabinet_started_at", "dissolution_date", "cabinet_source_url", "retrieved_at",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fields} for row in output_rows)


if __name__ == "__main__":
    main()
