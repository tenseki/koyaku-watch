#!/usr/bin/env python3
"""Build reproducible candidate and X-account CSVs from the LDP's official JSON."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from urllib.parse import urlparse


DETAIL_URL_BASE = "https://www.jimin.jp/election/results/sen_shu51/candidate/detail/"


def x_handle(url: str) -> str:
    """Return the profile handle when an official SNS URL is an X/Twitter profile."""
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    if host not in {"x.com", "twitter.com", "mobile.twitter.com"}:
        return ""
    return parsed.path.strip("/").split("/")[0].lstrip("@")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--all-output", type=Path, required=True)
    parser.add_argument("--x-output", type=Path, required=True)
    parser.add_argument("--retrieved-at", required=True)
    parser.add_argument("--source-url", required=True)
    args = parser.parse_args()

    candidates = json.loads(args.input.read_text(encoding="utf-8"))
    fields = [
        "candidate_key",
        "candidate_id",
        "candidate_slug",
        "name",
        "surname",
        "given_name",
        "surname_kana",
        "given_name_kana",
        "prefecture",
        "constituency",
        "proportional_block",
        "number_of_wins",
        "candidate_page_url",
        "official_x_url",
        "x_handle",
        "x_link_status",
        "source_json_url",
        "retrieved_at",
    ]

    rows = []
    for candidate in candidates:
        basic = candidate.get("basic", {})
        x_urls = [
            item.get("url", "").strip()
            for item in candidate.get("sns", [])
            if item.get("type") == "site_x" and item.get("url", "").strip()
        ]
        # Keep all official X links in the source JSON. The first is the primary
        # account for the analysis list; duplicates are recorded in the raw source.
        official_x_url = x_urls[0] if x_urls else ""
        slug = candidate.get("url", "")
        source_id = str(basic.get("mtentryid", ""))
        row = {
            # The detail-page slug is unique in the official list. Some records
            # use mtentryid=0, so that value is retained only as optional metadata.
            "candidate_key": slug.removesuffix(".html"),
            "candidate_id": "" if source_id == "0" else source_id,
            "candidate_slug": slug.removesuffix(".html"),
            "name": f"{basic.get('sei', '')}{basic.get('mei', '')}",
            "surname": basic.get("sei", ""),
            "given_name": basic.get("mei", ""),
            "surname_kana": basic.get("sei_kana", ""),
            "given_name_kana": basic.get("mei_kana", ""),
            "prefecture": basic.get("prefecture", ""),
            "constituency": basic.get("constituency", ""),
            "proportional_block": basic.get("proportional", ""),
            "number_of_wins": basic.get("number_of_wins", ""),
            "candidate_page_url": f"{DETAIL_URL_BASE}{slug}" if slug else "",
            "official_x_url": official_x_url,
            "x_handle": x_handle(official_x_url),
            "x_link_status": "official_link_listed" if official_x_url else "no_official_x_link_listed",
            "source_json_url": args.source_url,
            "retrieved_at": args.retrieved_at,
        }
        rows.append(row)

    for output, output_rows in (
        (args.all_output, rows),
        (args.x_output, [row for row in rows if row["official_x_url"]]),
    ):
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fields)
            writer.writeheader()
            writer.writerows(output_rows)


if __name__ == "__main__":
    main()
