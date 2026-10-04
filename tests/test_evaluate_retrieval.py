import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from evaluate_retrieval import evaluate_run, parse_labels


class EvaluateRetrievalTest(unittest.TestCase):
    def test_parse_labels(self) -> None:
        self.assertEqual({}, parse_labels("none"))
        self.assertEqual(
            {"A": "specific_measure", "B": "topic_only"},
            parse_labels("A=specific_measure|B=topic_only"),
        )
        self.assertEqual(
            {"A": "specific_measure", "B": "topic_only"},
            parse_labels(" A = specific_measure | B=topic_only "),
        )

    def test_keyword_and_rank_union(self) -> None:
        review = [
            {
                "post_id": "1",
                "human_verified": "true",
                "human_policy_labels": "A=specific_measure",
            },
            {
                "post_id": "2",
                "human_verified": "true",
                "human_policy_labels": "none",
            },
        ]
        rows = [
            {"policy_id": "A", "post_id": "1", "rank": "2", "keyword_matches": ""},
            {"policy_id": "A", "post_id": "2", "rank": "1", "keyword_matches": ""},
            {"policy_id": "B", "post_id": "1", "rank": "1", "keyword_matches": "hit"},
            {"policy_id": "B", "post_id": "2", "rank": "2", "keyword_matches": ""},
        ]
        result = evaluate_run(
            rows, review, {"specific": {"specific_measure"}}, [1, 2]
        )
        metrics = result["views"]["specific"]
        self.assertEqual(0, metrics["top_1"]["recovered_positive_pairs"])
        self.assertEqual(1, metrics["top_2"]["recovered_positive_pairs"])
        self.assertEqual(2, metrics["keyword_or_top_1"]["selected_pairs"])


if __name__ == "__main__":
    unittest.main()
