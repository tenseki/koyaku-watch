from __future__ import annotations

import unittest
import tempfile
from pathlib import Path

import numpy as np

from scripts.analysis_pipeline import (
    calculate_similarity_rows,
    select_labeling_candidates,
    write_csv,
)


class KeywordEncoder:
    def encode(self, texts: list[str]) -> np.ndarray:
        return np.asarray([
            [float("土地" in text), float("在留" in text), 0.1 + float("地方" in text)]
            for text in texts
        ])


POLICIES = [{
    "policy_id": "FOR-TEST-1",
    "title": "外国人の土地取得規制",
    "comparison_text": "外国人の土地取得を把握し規制する",
    "keywords": "土地取得|外国人土地取得",
}]


def post(index: int, candidate: str, text: str) -> dict[str, str]:
    return {
        "post_id": str(index), "candidate_key": candidate, "x_handle": candidate,
        "created_at": "2026-01-30T00:00:00+09:00", "post_type": "post",
        "post_url": f"https://example.invalid/{index}", "analysis_text": text,
        "is_analysis_target": "true",
    }


class AnalysisPipelineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.posts = [
            post(1, "a", "外国人の土地取得を把握する"),
            post(2, "b", "土地利用の新たなルール"),
            post(3, "c", "在留審査を厳格化する"),
            post(4, "d", "地方の交通を守る"),
            post(5, "e", "教育政策を進める"),
            post(6, "f", "防災訓練を実施する"),
        ]

    def similarity_rows(self) -> list[dict[str, str]]:
        return calculate_similarity_rows(
            POLICIES, self.posts, "test_set", ["title", "comparison_text", "keywords"],
            "検索クエリ: ", "検索文書: ", KeywordEncoder(),
        )

    def test_similarity_ranking_and_keyword_matches(self) -> None:
        rows = self.similarity_rows()
        self.assertEqual("1", rows[0]["post_id"])
        self.assertIn("土地取得", rows[0]["keyword_matches"])

    def test_labeling_selection_is_reproducible_and_deduplicated(self) -> None:
        rows = self.similarity_rows()
        first = select_labeling_candidates(rows, 2, 1, 1, 2026)
        self.assertEqual(first, select_labeling_candidates(rows, 2, 1, 1, 2026))
        self.assertEqual(len(first), len({row["post_id"] for row in first}))
        top = next(row for row in first if row["post_id"] == "1")
        self.assertIn("keyword_match", top["selection_reason"])
        self.assertIn("similarity_top", top["selection_reason"])
        self.assertIn("mention_level", top)
        self.assertIn("evidence_text", top)
        self.assertIn("judgment_reason", top)
        self.assertNotIn("label", top)

    def test_private_csv_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "private.csv"
            write_csv(path, ["value"], [{"value": "sensitive"}])
            self.assertEqual(0o600, path.stat().st_mode & 0o777)


if __name__ == "__main__":
    unittest.main()
