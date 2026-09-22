from __future__ import annotations

import unittest

from scripts.restore_post_review import restore_rows


class RestorePostReviewTest(unittest.TestCase):
    def test_preserves_only_human_fields(self) -> None:
        generated = [{
            "post_url": "https://example.invalid/1", "post_id": "123",
            "created_at": "2026-01-30T00:00:00Z", "human_policy_labels": "",
            "human_reason": "", "human_verified": "", "annotator": "",
            "reviewed_at": "",
        }]
        current = [{
            "post_url": "https://example.invalid/1", "post_id": "1.23E+2",
            "created_at": "46052", "human_policy_labels": "none",
            "human_reason": "confirmed", "human_verified": "TRUE",
            "annotator": "Tenseki", "reviewed_at": "2026-09-05",
        }]
        restored = restore_rows(generated, current)
        self.assertEqual("123", restored[0]["post_id"])
        self.assertEqual("2026-01-30T00:00:00Z", restored[0]["created_at"])
        self.assertEqual("none", restored[0]["human_policy_labels"])
        self.assertEqual("TRUE", restored[0]["human_verified"])


if __name__ == "__main__":
    unittest.main()
