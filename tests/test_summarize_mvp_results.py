import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from summarize_mvp_results import build_summary


class SummarizeMvpResultsTest(unittest.TestCase):
    def test_counts_posts_assignments_and_candidate_breadth(self) -> None:
        candidates = [{"candidate_key": "a"}, {"candidate_key": "b"}]
        policies = [
            {"policy_id": "P1", "category": "A", "title": "First"},
            {"policy_id": "P2", "category": "B", "title": "Second"},
        ]
        reviews = [
            {
                "post_id": "1", "candidate_key": "a", "post_type": "post",
                "human_verified": "true",
                "human_policy_labels": "P1=specific_measure|P2=policy_direction",
            },
            {
                "post_id": "2", "candidate_key": "b", "post_type": "reply",
                "human_verified": "true", "human_policy_labels": "none",
            },
        ]
        policy_output, summary = build_summary(reviews, policies, candidates, "test")
        self.assertEqual(1, summary["posts"]["specific_measure"])
        self.assertEqual(2, sum(summary["label_assignments"].values()))
        self.assertEqual(1, policy_output[0]["specific_measure_candidates"])
        self.assertEqual(0.5, policy_output[0]["specific_measure_density"])

    def test_rejects_unverified_rows(self) -> None:
        with self.assertRaisesRegex(ValueError, "unverified"):
            build_summary(
                [{
                    "post_id": "1", "candidate_key": "a", "post_type": "post",
                    "human_verified": "false", "human_policy_labels": "none",
                }],
                [{"policy_id": "P1", "category": "A", "title": "First"}],
                [{"candidate_key": "a"}],
                "test",
            )


if __name__ == "__main__":
    unittest.main()
