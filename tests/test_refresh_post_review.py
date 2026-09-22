import unittest

from scripts.refresh_post_review import refresh_rows


class RefreshPostReviewTest(unittest.TestCase):
    def test_preserves_order_batch_and_judgments_when_text_is_unchanged(self):
        generated = [
            {"post_id": "2", "review_batch": "1", "analysis_text": "same", "review_stratum": "new"},
            {"post_id": "1", "review_batch": "2", "analysis_text": "same", "review_stratum": "new"},
        ]
        current = [
            {"post_id": "1", "review_batch": "1", "analysis_text": "same", "ai_policy_labels": "none", "human_verified": "TRUE"},
            {"post_id": "2", "review_batch": "2", "analysis_text": "same", "ai_policy_labels": "none", "human_verified": "TRUE"},
        ]

        refreshed, invalidated = refresh_rows(generated, current)

        self.assertEqual([row["post_id"] for row in refreshed], ["1", "2"])
        self.assertEqual([row["review_batch"] for row in refreshed], ["1", "2"])
        self.assertEqual(refreshed[0]["ai_policy_labels"], "none")
        self.assertEqual(refreshed[0]["human_verified"], "TRUE")
        self.assertEqual(invalidated, [])

    def test_clears_ai_and_human_judgments_when_text_changes(self):
        generated = [{"post_id": "1", "review_batch": "9", "analysis_text": "full"}]
        current = [{
            "post_id": "1", "review_batch": "3", "analysis_text": "short",
            "ai_policy_labels": "none", "human_policy_labels": "none",
            "human_verified": "TRUE", "annotator": "person", "reviewed_at": "2026-09-05",
        }]

        refreshed, invalidated = refresh_rows(generated, current)

        self.assertEqual(refreshed[0]["review_batch"], "3")
        self.assertEqual(refreshed[0]["analysis_text"], "full")
        self.assertEqual(refreshed[0]["ai_policy_labels"], "")
        self.assertEqual(refreshed[0]["human_verified"], "")
        self.assertEqual(invalidated, ["1"])


if __name__ == "__main__":
    unittest.main()
