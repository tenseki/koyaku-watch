import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import count_x_posts


class CountXPostsTest(unittest.TestCase):
    @mock.patch("scripts.count_x_posts.api_get")
    def test_count_posts_uses_meta_total(self, api_get):
        api_get.return_value = {
            "data": [
                {"start": "a", "end": "b", "tweet_count": 2},
                {"start": "b", "end": "c", "tweet_count": 3},
            ],
            "meta": {"total_tweet_count": 5},
        }

        result = count_x_posts.count_posts("token", "candidate", "start", "end")

        self.assertEqual(result["total"], 5)
        self.assertEqual(api_get.call_args.args[0], "/tweets/counts/all")

    def test_write_and_read_existing_round_trip(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "counts.csv"
            row = {field: "value" for field in count_x_posts.OUTPUT_FIELDS}
            row["candidate_key"] = "candidate-a"

            count_x_posts.write_rows(path, [row])

            self.assertEqual(
                count_x_posts.read_existing(path)["candidate-a"]["name"],
                "value",
            )
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
