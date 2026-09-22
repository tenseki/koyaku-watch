#!/usr/bin/env python3
"""Preprocess a canonical post CSV for the analysis pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from post_processing import (
    load_target_scope,
    preprocess_rows,
    read_post_csv,
    validate_target_scope,
    write_processed_csv,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Preprocess canonical X post rows.")
    parser.add_argument("--analysis-config", type=Path, required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = read_post_csv(args.input)
    candidate_keys, start_time, end_time = load_target_scope(args.analysis_config)
    validate_target_scope(rows, candidate_keys, start_time, end_time)
    processed = preprocess_rows(rows)
    write_processed_csv(args.output, processed)
    included = sum(row["is_analysis_target"] == "true" for row in processed)
    print(
        f"wrote {len(processed)} posts to {args.output} "
        f"({included} included, {len(processed) - included} excluded)"
    )


if __name__ == "__main__":
    main()
