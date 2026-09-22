from __future__ import annotations

import unittest

from scripts.apply_ai_review import apply_suggestions


class ApplyAiReviewTest(unittest.TestCase):
    def test_applies_none_and_policy_suggestions_with_provenance(self) -> None:
        rows = [{"post_id": "1"}, {"post_id": "2"}]
        suggestions = [
            {"post_id": "1", "policy_labels": "none", "reason": "no policy", "confidence": "high"},
            {"post_id": "2", "policy_labels": "P1=topic_only", "reason": "topic", "confidence": "medium"},
        ]
        errors = apply_suggestions(
            rows, suggestions, {"P1": "Policy 1"}, {"topic_only"}, "model", "1.0"
        )
        self.assertEqual([], errors)
        self.assertEqual("none", rows[0]["ai_policy_labels"])
        self.assertEqual("Policy 1", rows[1]["ai_policy_titles"])
        self.assertEqual("model", rows[1]["ai_model"])


if __name__ == "__main__":
    unittest.main()
