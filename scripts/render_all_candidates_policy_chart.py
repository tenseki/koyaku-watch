#!/usr/bin/env python3
"""Render the all-candidate policy-mention composition as a public-safe SVG."""

from __future__ import annotations

import argparse
import csv
from html import escape
from pathlib import Path


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    if not rows:
        raise ValueError("policy summary has no rows")
    return rows


def render_svg(rows: list[dict[str, str]], denominator: int) -> str:
    width = 1600
    row_height = 52
    first_y = 226
    bottom = 142
    height = first_y + row_height * len(rows) + bottom
    plot_left, plot_right = 550, 1300
    plot_width = plot_right - plot_left
    max_rate = 22.0
    colors = {
        "specific": "#2368a2",
        "direction": "#d27328",
        "topic": "#6f7b86",
    }
    text_color, muted_color, grid_color = "#17212b", "#5f6b76", "#d9dee3"

    def rate(count: int) -> float:
        return count / denominator * 100

    def x(value: float) -> float:
        return plot_left + min(value, max_rate) / max_rate * plot_width

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<style>',
        f'text {{ font-family: "Noto Sans CJK JP", "Yu Gothic", "Hiragino Sans", sans-serif; fill: {text_color}; }}',
        f'.title {{ font-size: 34px; font-weight: 700; }} .subtitle {{ font-size: 19px; fill: {muted_color}; }}',
        f'.label {{ font-size: 16px; }} .code {{ font-size: 13px; fill: {muted_color}; }}',
        f'.axis {{ font-size: 15px; fill: {muted_color}; }} .value {{ font-size: 14px; font-variant-numeric: tabular-nums; }}',
        f'.note {{ font-size: 16px; fill: {muted_color}; }}',
        '</style>',
        '<text class="title" x="40" y="52">政策言及投稿の内訳</text>',
        '<text class="subtitle" x="40" y="86">対象：全229候補のうち、事前に定めた23政策に言及した197投稿（2026年1月30日〜2月3日・日本時間）</text>',
    ]
    legend = [("specific", "具体策"), ("direction", "政策方向"), ("topic", "分野のみ")]
    for index, (key, label) in enumerate(legend):
        left = 40 + index * 160
        parts += [
            f'<rect x="{left}" y="112" width="24" height="8" fill="{colors[key]}"/>',
            f'<text class="label" x="{left + 34}" y="122">{label}</text>',
        ]
    parts += [
        '<text class="axis" x="40" y="174">政策項目</text>',
        '<text class="axis" x="1400" y="174" text-anchor="middle">件数</text>',
        '<text class="axis" x="1530" y="174" text-anchor="middle">候補者数</text>',
    ]
    for tick in range(0, 23, 2):
        tick_x = x(float(tick))
        parts += [
            f'<line x1="{tick_x:.1f}" y1="184" x2="{tick_x:.1f}" y2="{first_y + row_height * len(rows) - 22}" stroke="{grid_color}" stroke-width="1"/>',
            f'<text class="axis" x="{tick_x:.1f}" y="174" text-anchor="middle">{tick}%</text>',
        ]

    previous_category = ""
    for index, row in enumerate(rows):
        y = first_y + index * row_height
        if previous_category and row["category"] != previous_category:
            parts.append(f'<line x1="40" y1="{y - 26}" x2="1560" y2="{y - 26}" stroke="{grid_color}" stroke-width="1"/>')
        previous_category = row["category"]
        specific = int(row["specific_measure_posts"])
        direction = int(row["policy_direction_posts"])
        topic = int(row["topic_only_posts"])
        parts += [
            f'<text class="label" x="40" y="{y + 4}">{escape(row["policy_title"])}</text>',
            f'<text class="code" x="520" y="{y + 4}" text-anchor="end">{escape(row["policy_id"])}</text>',
        ]
        for offset, count, color in ((-10, specific, colors["specific"]), (0, direction, colors["direction"]), (10, topic, colors["topic"])):
            if count:
                value = rate(count)
                parts.append(f'<rect x="{plot_left}" y="{y + offset - 3}" width="{x(value) - plot_left:.1f}" height="6" fill="{color}"/>')
        parts += [
            f'<text class="value" x="1400" y="{y + 4}" text-anchor="middle">{specific} / {direction} / {topic}</text>',
            f'<text class="value" x="1530" y="{y + 4}" text-anchor="middle">{row["direction_or_more_candidates"]} / 229</text>',
        ]

    axis_y = first_y + row_height * len(rows) - 22
    parts += [
        f'<line x1="{plot_left}" y1="{axis_y}" x2="{plot_right}" y2="{axis_y}" stroke="{text_color}" stroke-width="1"/>',
        f'<text class="axis" x="{(plot_left + plot_right) / 2:.1f}" y="{axis_y + 34}" text-anchor="middle">政策言及投稿197件に占める割合</text>',
        f'<text class="note" x="40" y="{height - 62}">「政策方向」は具体策を含まない。バーは各区分の投稿数を197投稿で割った割合。</text>',
        f'<text class="note" x="40" y="{height - 32}">1投稿が複数政策に触れるため、政策別の割合を合計して100%にはならない。判定保留2件は区分バーに含めない。</text>',
        '</svg>',
    ]
    return "\n".join(parts) + "\n"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=root / "data/all_candidates_policy_summary_2026.csv")
    parser.add_argument("--denominator", type=int, default=197)
    parser.add_argument("--output", type=Path, default=root / "assets/charts/全候補者_23政策_政策言及内訳_197投稿.svg")
    args = parser.parse_args()
    if args.denominator <= 0:
        raise ValueError("denominator must be positive")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_svg(read_rows(args.input), args.denominator), encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
