from __future__ import annotations

import unittest

from scripts.validate_labeling import validate_rows


CONFIG = {
    "human_labeling": {
        "field": "mention_level",
        "evidence_field": "evidence_text",
        "reason_code_field": "judgment_reason_code",
        "reason_field": "judgment_reason",
        "allowed_labels": [
            "specific_measure", "policy_direction", "topic_only", "none", "uncertain"
        ],
        "allowed_reason_codes": [
            "target_specific_measure", "target_policy_direction", "target_topic_only",
            "election_call_only", "campaign_event_notice_only", "unrelated_topic",
            "insufficient_context", "ambiguous_policy_mapping", "other",
        ],
    }
}


def row(label: str, code: str, evidence: str = "") -> dict[str, str]:
    return {
        "policy_id": "P-1",
        "post_id": "1",
        "mention_level": label,
        "evidence_text": evidence,
        "judgment_reason_code": code,
        "judgment_reason": "",
    }


class ValidateLabelingTest(unittest.TestCase):
    def test_accepts_generic_election_call_as_none(self) -> None:
        self.assertEqual([], validate_rows([row("none", "election_call_only")], CONFIG))

    def test_positive_label_requires_matching_code_and_evidence(self) -> None:
        errors = validate_rows(
            [row("specific_measure", "target_policy_direction")], CONFIG
        )
        self.assertEqual(2, len(errors))

    def test_incomplete_row_is_optional_until_final_validation(self) -> None:
        blank = row("", "")
        self.assertEqual([], validate_rows([blank], CONFIG))
        self.assertEqual(1, len(validate_rows([blank], CONFIG, require_complete=True)))


if __name__ == "__main__":
    unittest.main()
