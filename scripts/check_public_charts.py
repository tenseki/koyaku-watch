#!/usr/bin/env python3
"""Rebuild public SVGs in a temporary directory and require byte equality."""
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CHARTS = (
    ("scripts/render_mvp_policy_chart.py",
     "data/mvp_policy_summary_2026.csv",
     "assets/charts/MVP_23政策_言及率_全487投稿.svg"),
    ("scripts/render_all_candidates_policy_chart.py",
     "data/all_candidates_policy_summary_2026.csv",
     "assets/charts/全候補者_23政策_政策言及内訳_197投稿.svg"),
)


def main():
    mismatches = []
    with tempfile.TemporaryDirectory(prefix="koyaku-charts-") as directory:
        for index, (script, source, reference) in enumerate(CHARTS):
            output = Path(directory) / f"chart-{index}.svg"
            subprocess.run(
                [sys.executable, str(ROOT / script), "--input", str(ROOT / source),
                 "--output", str(output)], check=True, cwd=ROOT, capture_output=True,
            )
            if output.read_bytes() != (ROOT / reference).read_bytes():
                mismatches.append(reference)
                print(f"SVG mismatch: {reference}", file=sys.stderr)
            else:
                print(f"SVG matches: {reference}")
    if mismatches:
        print("Review the CSV, renderer and saved SVG together; do not overwrite a fixed release silently.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
