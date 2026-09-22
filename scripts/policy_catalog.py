#!/usr/bin/env python3
"""Load and validate policy catalogs and named policy sets."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


REQUIRED_FIELDS = {
    "policy_id",
    "topic_group",
    "category",
    "title",
    "comparison_text",
    "keywords",
    "source_text",
    "source_document",
    "source_pages",
    "source_url",
    "specificity",
    "segmentation_rule",
    "notes",
}


def load_config(config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(config.get("sets"), dict) or not config["sets"]:
        raise ValueError("policy config must contain a non-empty 'sets' object")
    if config.get("default_set") not in config["sets"]:
        raise ValueError("default_set is not defined in sets")
    return config


def resolve_catalog_path(config_path: Path, config: dict[str, Any]) -> Path:
    catalog = config.get("catalog")
    if not isinstance(catalog, str) or not catalog:
        raise ValueError("policy config must contain a catalog path")
    path = Path(catalog)
    return path if path.is_absolute() else (config_path.parent / path).resolve()


def load_catalog(catalog_path: Path) -> tuple[list[str], dict[str, dict[str, str]]]:
    with catalog_path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        fields = reader.fieldnames or []
        missing = REQUIRED_FIELDS.difference(fields)
        if missing:
            raise ValueError(f"catalog fields missing: {', '.join(sorted(missing))}")

        rows: dict[str, dict[str, str]] = {}
        for line_number, row in enumerate(reader, start=2):
            policy_id = row["policy_id"].strip()
            if not policy_id:
                raise ValueError(f"empty policy_id at line {line_number}")
            if policy_id in rows:
                raise ValueError(f"duplicate policy_id: {policy_id}")
            for field in ("title", "comparison_text", "source_text", "source_pages"):
                if not row[field].strip():
                    raise ValueError(f"{field} is empty for {policy_id}")
            rows[policy_id] = row

    return fields, rows


def select_policy_rows(
    config_path: Path, set_name: str
) -> tuple[list[str], list[dict[str, str]], dict[str, Any]]:
    config = load_config(config_path)
    if set_name not in config["sets"]:
        available = ", ".join(sorted(config["sets"]))
        raise ValueError(f"unknown policy set '{set_name}'; available: {available}")

    catalog_path = resolve_catalog_path(config_path, config)
    fields, catalog = load_catalog(catalog_path)
    policy_ids = config["sets"][set_name].get("policy_ids")
    if not isinstance(policy_ids, list) or not policy_ids:
        raise ValueError(f"policy set '{set_name}' has no policy_ids")
    if len(policy_ids) != len(set(policy_ids)):
        raise ValueError(f"policy set '{set_name}' contains duplicate policy_ids")

    missing = [policy_id for policy_id in policy_ids if policy_id not in catalog]
    if missing:
        raise ValueError(f"policy_ids not found in catalog: {', '.join(missing)}")

    return fields, [catalog[policy_id] for policy_id in policy_ids], config
