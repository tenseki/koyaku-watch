from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "analysis_mvp_2026.json"


class AnalysisConfigTest(unittest.TestCase):
    def setUp(self) -> None:
        self.config = json.loads(CONFIG.read_text(encoding="utf-8"))

    def test_five_level_label_scheme_is_fixed(self) -> None:
        self.assertEqual(
            [
                "specific_measure",
                "policy_direction",
                "topic_only",
                "none",
                "uncertain",
            ],
            self.config["human_labeling"]["allowed_labels"],
        )

    def test_named_analysis_views_keep_topic_only_separate(self) -> None:
        views = self.config["analysis_views"]
        self.assertEqual(["specific_measure"], views["specific_measure_only"])
        self.assertEqual(
            ["specific_measure", "policy_direction"],
            views["policy_direction_or_more"],
        )
        self.assertEqual(["topic_only"], views["topic_context_only"])

    def test_embedding_is_selected_retrieval_baseline(self) -> None:
        embedding = self.config["embedding"]
        self.assertEqual("candidate_retrieval_baseline", embedding["role"])
        self.assertEqual(
            "selected_after_exhaustive_mvp_validation", embedding["status"]
        )
        self.assertEqual(
            "keyword_match_or_similarity_top_3", embedding["selection_rule"]
        )

    def test_structured_labeling_reason_codes_are_fixed(self) -> None:
        labeling = self.config["human_labeling"]
        self.assertEqual("1.0", labeling["rules_version"])
        self.assertEqual("judgment_reason_code", labeling["reason_code_field"])
        self.assertIn("election_call_only", labeling["allowed_reason_codes"])
        self.assertIn("campaign_event_notice_only", labeling["allowed_reason_codes"])


if __name__ == "__main__":
    unittest.main()
