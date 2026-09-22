#!/usr/bin/env python3
"""Render the public MVP policy summary as a publication-ready SVG."""

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


def render_svg(rows: list[dict[str, str]]) -> str:
    width = 1600
    row_height = 46
    first_y = 214
    bottom = 128
    height = first_y + row_height * len(rows) + bottom
    plot_left = 535
    plot_right = 1320
    plot_width = plot_right - plot_left
    max_rate = 5.0

    specific_color = "#2368a2"
    direction_color = "#d27328"
    text_color = "#17212b"
    muted_color = "#5f6b76"
    grid_color = "#d9dee3"

    def rate(row: dict[str, str], field: str) -> float:
        return float(row[field]) * 100

    def x(value: float) -> float:
        return plot_left + min(value, max_rate) / max_rate * plot_width

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<style>',
        'text { font-family: "Noto Sans CJK JP", "Yu Gothic", "Hiragino Sans", sans-serif; fill: #17212b; }',
        '.title { font-size: 34px; font-weight: 700; }',
        '.subtitle { font-size: 19px; fill: #5f6b76; }',
        '.label { font-size: 16px; }',
        '.code { font-size: 13px; fill: #5f6b76; }',
        '.axis { font-size: 15px; fill: #5f6b76; }',
        '.value { font-size: 15px; font-variant-numeric: tabular-nums; }',
        '.note { font-size: 16px; fill: #5f6b76; }',
        '</style>',
        '<text class="title" x="40" y="52">23政策の言及率</text>',
        '<text class="subtitle" x="40" y="86">対象：13アカウント・487投稿（2026年1月30日〜2月3日）</text>',
        f'<rect x="40" y="112" width="24" height="8" fill="{specific_color}"/>',
        '<text class="label" x="74" y="122">具体策</text>',
        f'<rect x="165" y="112" width="24" height="8" fill="{direction_color}"/>',
        '<text class="label" x="199" y="122">政策方向以上</text>',
        '<text class="subtitle" x="384" y="122">○は0件</text>',
        '<text class="axis" x="40" y="174">政策項目</text>',
        '<text class="axis" x="1408" y="174" text-anchor="middle">具体 / 方向</text>',
        '<text class="axis" x="1532" y="174" text-anchor="middle">発信者数</text>',
    ]

    for tick in range(6):
        tick_x = x(float(tick))
        parts.append(
            f'<line x1="{tick_x:.1f}" y1="184" x2="{tick_x:.1f}" '
            f'y2="{first_y + row_height * len(rows) - 18}" stroke="{grid_color}" stroke-width="1"/>'
        )
        parts.append(
            f'<text class="axis" x="{tick_x:.1f}" y="174" text-anchor="middle">{tick}%</text>'
        )

    previous_category = ""
    for index, row in enumerate(rows):
        y = first_y + index * row_height
        category = row["category"]
        if previous_category and category != previous_category:
            parts.append(
                f'<line x1="40" y1="{y - 23}" x2="1560" y2="{y - 23}" '
                f'stroke="{grid_color}" stroke-width="1"/>'
            )
        previous_category = category

        label = escape(row["policy_title"])
        code = escape(row["policy_id"])
        specific = rate(row, "specific_measure_density")
        direction = rate(row, "direction_or_more_density")
        specific_count = int(row["specific_measure_posts"])
        direction_count = int(row["direction_or_more_posts"])
        candidates = int(row["direction_or_more_candidates"])

        parts.append(f'<text class="label" x="40" y="{y + 4}">{label}</text>')
        parts.append(f'<text class="code" x="505" y="{y + 4}" text-anchor="end">{code}</text>')

        for value, lane_y, color, count in (
            (specific, y - 8, specific_color, specific_count),
            (direction, y + 6, direction_color, direction_count),
        ):
            if count:
                bar_width = x(value) - plot_left
                parts.append(
                    f'<rect x="{plot_left}" y="{lane_y}" width="{bar_width:.1f}" '
                    f'height="7" fill="{color}"/>'
                )
                parts.append(
                    f'<circle cx="{x(value):.1f}" cy="{lane_y + 3.5}" r="4.5" fill="{color}"/>'
                )
            else:
                parts.append(
                    f'<circle cx="{plot_left}" cy="{lane_y + 3.5}" r="4" '
                    f'fill="#ffffff" stroke="{color}" stroke-width="2"/>'
                )

        parts.append(
            f'<text class="value" x="1408" y="{y + 4}" text-anchor="middle">'
            f'{specific:.1f}% / {direction:.1f}%</text>'
        )
        parts.append(
            f'<text class="value" x="1532" y="{y + 4}" text-anchor="middle">{candidates} / 13</text>'
        )

    axis_y = first_y + row_height * len(rows) - 18
    parts.extend([
        f'<line x1="{plot_left}" y1="{axis_y}" x2="{plot_right}" y2="{axis_y}" stroke="{text_color}" stroke-width="1"/>',
        f'<text class="axis" x="{(plot_left + plot_right) / 2:.1f}" y="{axis_y + 34}" text-anchor="middle">全487投稿に占める割合</text>',
        f'<text class="note" x="40" y="{height - 56}">具体策が0件：16 / 23政策。政策方向以上が0件：13 / 23政策。</text>',
        f'<text class="note" x="40" y="{height - 28}">注：最多24件は、同一アカウントによる地域別投稿シリーズ。発信者数を併記し、投稿回数と発信の広がりを区別した。</text>',
        '</svg>',
    ])
    return "\n".join(parts) + "\n"


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", type=Path, default=root / "data/mvp_policy_summary_2026.csv"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "assets/charts/MVP_23政策_言及率_全487投稿.svg",
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render_svg(read_rows(args.input)), encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
