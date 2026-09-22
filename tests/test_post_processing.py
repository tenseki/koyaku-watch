from __future__ import annotations

import unittest
from datetime import datetime

from scripts.post_processing import normalize_text, preprocess_rows, validate_target_scope


def row(post_id: str, post_type: str, raw_text: str) -> dict[str, str]:
    return {
        "post_id": post_id,
        "candidate_key": "candidate-a",
        "author_id": "author-a",
        "x_handle": "candidate_a",
        "created_at": "2026-01-30T00:00:00+09:00",
        "post_type": post_type,
        "raw_text": raw_text,
        "post_url": f"https://example.invalid/{post_id}",
        "has_media": "false",
        "retrieved_at": "2026-08-30T00:00:00+09:00",
    }


class PostProcessingTest(unittest.TestCase):
    def test_normalize_removes_urls_mentions_and_keeps_hashtags(self) -> None:
        self.assertEqual("政策です #公約", normalize_text("@someone  政策です\n#公約 https://example.com/a"))

    def test_repost_and_empty_text_are_excluded(self) -> None:
        processed = preprocess_rows([
            row("1", "repost", "RT @someone テキスト"),
            row("2", "post", "https://example.com/image"),
            row("3", "reply", "@someone 在留審査を厳格化します"),
        ])
        self.assertEqual("simple_repost", processed[0]["exclusion_reason"])
        self.assertEqual("empty_after_preprocessing", processed[1]["exclusion_reason"])
        self.assertEqual("true", processed[2]["is_analysis_target"])

    def test_duplicate_post_id_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicate post_id"):
            preprocess_rows([row("1", "post", "a"), row("1", "post", "b")])

    def test_target_scope_rejects_unknown_candidate_and_outside_date(self) -> None:
        start = datetime.fromisoformat("2026-01-30T00:00:00+09:00")
        end = datetime.fromisoformat("2026-02-04T00:00:00+09:00")
        with self.assertRaisesRegex(ValueError, "outside target scope"):
            validate_target_scope([row("1", "post", "a")], {"candidate-b"}, start, end)
        outside = row("2", "post", "a")
        outside["created_at"] = "2026-02-04T00:00:00+09:00"
        with self.assertRaisesRegex(ValueError, "outside target period"):
            validate_target_scope([outside], {"candidate-a"}, start, end)


if __name__ == "__main__":
    unittest.main()
