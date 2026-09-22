from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from scripts.build_analysis_corpus import build_corpus


FIELDS = ["post_id", "candidate_key", "is_analysis_target"]


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)


class BuildAnalysisCorpusTest(unittest.TestCase):
    def test_combines_files_in_declared_candidate_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            write_rows(
                root / "a_posts.processed.csv",
                [{"post_id": "2", "candidate_key": "a", "is_analysis_target": "true"}],
            )
            write_rows(
                root / "b_posts.processed.csv",
                [{"post_id": "1", "candidate_key": "b", "is_analysis_target": "false"}],
            )
            fields, rows = build_corpus(root, ["a", "b"])
            self.assertEqual(FIELDS, fields)
            self.assertEqual(["2", "1"], [row["post_id"] for row in rows])

    def test_rejects_duplicate_post_ids_across_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for candidate in ("a", "b"):
                write_rows(
                    root / f"{candidate}_posts.processed.csv",
                    [{
                        "post_id": "1",
                        "candidate_key": candidate,
                        "is_analysis_target": "true",
                    }],
                )
            with self.assertRaisesRegex(ValueError, "duplicate post_id"):
                build_corpus(root, ["a", "b"])


if __name__ == "__main__":
    unittest.main()
