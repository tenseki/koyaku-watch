import unittest

from scripts.build_post_review_audit import (
    duplicate_label_conflicts,
    select_audit_rows,
)


class PostReviewAuditTest(unittest.TestCase):
    def test_selects_random_and_risk_rows_without_duplicates(self) -> None:
        rows = [
            {
                "post_id": str(index),
                "human_policy_labels": "none",
                "ai_confidence": "medium" if index == 0 else "high",
                "retrieval_policy_ids": "ECO-001" if index == 1 else "",
            }
            for index in range(10)
        ]
        selected, random_ids, risk_ids = select_audit_rows(rows, 3, 20260905)
        self.assertEqual({"0", "1"}, risk_ids)
        self.assertEqual(3, len(random_ids))
        self.assertEqual(len(random_ids | risk_ids), len(selected))

    def test_detects_inconsistent_exact_duplicates(self) -> None:
        rows = [
            {"analysis_text": "same", "human_policy_labels": "none"},
            {"analysis_text": "same", "human_policy_labels": "ECO-001=topic_only"},
            {"analysis_text": "other", "human_policy_labels": "none"},
        ]
        self.assertEqual(1, len(duplicate_label_conflicts(rows)))


if __name__ == "__main__":
    unittest.main()
