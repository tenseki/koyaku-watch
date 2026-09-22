import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts import fetch_x_batch


class FetchXBatchTest(unittest.TestCase):
    def test_completed_output_requires_matching_hash_and_count(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "candidate_posts.csv"
            output.write_text("post_id\n1\n", encoding="utf-8")
            metadata = root / "candidate_posts.metadata.json"
            metadata.write_text(
                json.dumps({
                    "retrieved_count": 1,
                    "more_results_available": False,
                    "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
                }),
                encoding="utf-8",
            )

            self.assertTrue(fetch_x_batch.completed_output(output, metadata))
            output.write_text("post_id\n2\n", encoding="utf-8")
            self.assertFalse(fetch_x_batch.completed_output(output, metadata))

    def test_load_candidate_keys_validates_configured_count(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            candidate_file = root / "candidates.csv"
            with candidate_file.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=["candidate_key"])
                writer.writeheader()
                writer.writerow({"candidate_key": "a"})
                writer.writerow({"candidate_key": "b"})
            config = root / "analysis.json"
            config.write_text(json.dumps({
                "target": {"candidate_file": "candidates.csv", "candidate_count": 2}
            }), encoding="utf-8")

            self.assertEqual(fetch_x_batch.load_candidate_keys(config), ["a", "b"])


if __name__ == "__main__":
    unittest.main()
