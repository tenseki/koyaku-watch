import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import fetch_x_posts


class FetchXPostsTest(unittest.TestCase):
    def test_classify_post_uses_reference_type(self):
        self.assertEqual("post", fetch_x_posts.classify_post({}))
        self.assertEqual(
            "reply",
            fetch_x_posts.classify_post({"referenced_tweets": [{"type": "replied_to"}]}),
        )
        self.assertEqual(
            "quote",
            fetch_x_posts.classify_post({"referenced_tweets": [{"type": "quoted"}]}),
        )
        self.assertEqual(
            "repost",
            fetch_x_posts.classify_post({"referenced_tweets": [{"type": "retweeted"}]}),
        )

    def test_post_to_row_matches_canonical_schema(self):
        post = {
            "id": "123",
            "author_id": "456",
            "created_at": "2026-01-30T00:00:00Z",
            "text": "政策について",
            "attachments": {"media_keys": ["media-1"]},
        }
        candidate = {
            "candidate_key": "candidate-a",
            "x_handle": "candidate_a",
        }

        row = fetch_x_posts.post_to_row(post, candidate, "2026-08-30T00:00:00Z")

        self.assertEqual(set(row), set(fetch_x_posts.INPUT_FIELDS))
        self.assertEqual(row["post_type"], "post")
        self.assertEqual(row["has_media"], "true")
        self.assertEqual(row["post_url"], "https://x.com/candidate_a/status/123")

    def test_post_to_row_prefers_note_tweet_text(self):
        post = {
            "id": "123",
            "author_id": "456",
            "created_at": "2026-01-30T00:00:00Z",
            "text": "通常textの省略本文",
            "note_tweet": {"text": "note_tweetに入った長文投稿の全文"},
        }
        candidate = {
            "candidate_key": "candidate-a",
            "x_handle": "candidate_a",
        }

        row = fetch_x_posts.post_to_row(post, candidate, "2026-08-30T00:00:00Z")

        self.assertEqual(row["raw_text"], "note_tweetに入った長文投稿の全文")

    def test_full_post_text_falls_back_when_note_tweet_is_missing_or_empty(self):
        self.assertEqual(fetch_x_posts.full_post_text({"text": "通常文"}), "通常文")
        self.assertEqual(
            fetch_x_posts.full_post_text(
                {"text": "通常文", "note_tweet": {"text": ""}}
            ),
            "通常文",
        )

    @mock.patch("scripts.fetch_x_posts.api_get")
    def test_fetch_pages_stops_at_page_limit_and_reports_more_results(self, api_get):
        api_get.return_value = {
            "data": [{"id": "1"}],
            "meta": {"next_token": "more"},
        }

        posts, pagination = fetch_x_posts.fetch_pages(
            "token", "candidate_a", "start", "end", 10, 1
        )

        self.assertEqual(posts, [{"id": "1"}])
        self.assertEqual(pagination["pages_fetched"], 1)
        self.assertTrue(pagination["more_results_available"])
        self.assertIn("note_tweet", api_get.call_args.args[2]["tweet.fields"])

    @mock.patch("scripts.fetch_x_posts.api_get")
    def test_fetch_pages_deduplicates_post_ids_across_pages(self, api_get):
        api_get.side_effect = [
            {
                "data": [{"id": "1"}, {"id": "2"}],
                "meta": {"next_token": "page-2"},
            },
            {
                "data": [{"id": "2"}, {"id": "3"}],
                "meta": {},
            },
        ]

        posts, pagination = fetch_x_posts.fetch_pages(
            "token", "candidate_a", "start", "end", 10, 2,
            request_interval_seconds=0,
        )

        self.assertEqual([post["id"] for post in posts], ["1", "2", "3"])
        self.assertEqual(pagination["duplicates_ignored"], 1)
        self.assertFalse(pagination["more_results_available"])

    def test_load_plan_resolves_candidate_from_config(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "data").mkdir()
            with (root / "data" / "candidates.csv").open(
                "w", encoding="utf-8", newline=""
            ) as file:
                writer = csv.DictWriter(file, fieldnames=["candidate_key", "x_handle"])
                writer.writeheader()
                writer.writerow({"candidate_key": "candidate-a", "x_handle": "candidate_a"})
            config = {
                "target": {
                    "candidate_file": "../data/candidates.csv",
                    "start_time_utc": "2026-01-29T15:00:00Z",
                    "end_time_utc_exclusive": "2026-02-03T15:00:00Z",
                }
            }
            (root / "config").mkdir()
            config_path = root / "config" / "analysis.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")

            plan = fetch_x_posts.load_plan(config_path, "candidate-a")

            self.assertEqual(plan["candidate"]["x_handle"], "candidate_a")


if __name__ == "__main__":
    unittest.main()
