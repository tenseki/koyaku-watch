from __future__ import annotations

import unittest

from scripts.validate_post_review import parse_policy_labels, validate_rows


CONFIG = {
    "human_labeling": {
        "allowed_labels": [
            "specific_measure", "policy_direction", "topic_only", "none", "uncertain"
        ]
    },
    "post_review": {"allowed_confidence": ["high", "medium", "low"]},
}


def row() -> dict[str, str]:
    return {
        "post_id": "1", "ai_policy_labels": "", "ai_confidence": "",
        "ai_model": "", "ai_rules_version": "", "human_policy_labels": "",
        "human_verified": "", "annotator": "", "reviewed_at": "",
    }


class ValidatePostReviewTest(unittest.TestCase):
    def test_label_format_accepts_none_and_multiple_policies(self) -> None:
        self.assertEqual([], parse_policy_labels("none", {"P1"}, {"topic_only"}))
        self.assertEqual(
            [],
            parse_policy_labels(
                "P1=topic_only|P2=specific_measure",
                {"P1", "P2"},
                {"topic_only", "specific_measure"},
            ),
        )

    def test_ai_label_requires_provenance(self) -> None:
        value = row()
        value["ai_policy_labels"] = "none"
        self.assertEqual(3, len(validate_rows([value], CONFIG, {"P1"})))

    def test_verified_human_label_requires_metadata(self) -> None:
        value = row()
        value["human_verified"] = "true"
        self.assertEqual(3, len(validate_rows([value], CONFIG, {"P1"})))


if __name__ == "__main__":
    unittest.main()
