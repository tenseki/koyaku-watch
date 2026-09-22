from __future__ import annotations

import unittest

from scripts.build_post_review import build_review_rows


def post(post_id: str, text: str) -> dict[str, str]:
    return {
        "post_id": post_id,
        "candidate_key": "candidate",
        "x_handle": "handle",
        "created_at": "2026-01-30T00:00:00Z",
        "post_type": "post",
        "post_url": f"https://example.invalid/{post_id}",
        "analysis_text": text,
        "is_analysis_target": "true",
    }


class BuildPostReviewTest(unittest.TestCase):
    def test_builds_one_row_per_analysis_target(self) -> None:
        posts = [post("1", "期日前投票をお願いします"), post("2", "政策を進めます")]
        retrieval = {"1": {"P-1": {"similarity_top"}}}
        rows = build_review_rows(posts, retrieval, {"P-1": "政策1"}, 1, 2026)
        self.assertEqual(2, len(rows))
        first = next(row for row in rows if row["post_id"] == "1")
        self.assertEqual("retrieval_and_generic", first["review_stratum"])
        self.assertEqual("P-1", first["retrieval_policy_ids"])
        self.assertIn("election_call", first["screening_hints"])

    def test_excludes_non_target_posts(self) -> None:
        excluded = post("1", "リポスト")
        excluded["is_analysis_target"] = "false"
        self.assertEqual([], build_review_rows([excluded], {}, {}, 40, 2026))


if __name__ == "__main__":
    unittest.main()
