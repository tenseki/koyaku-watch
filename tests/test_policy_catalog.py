from __future__ import annotations

import unittest
from pathlib import Path

from scripts.policy_catalog import load_catalog, load_config, resolve_catalog_path, select_policy_rows


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "policy_sets_2026.json"


class PolicyCatalogTest(unittest.TestCase):
    def test_catalog_has_unique_23_policies(self) -> None:
        config = load_config(CONFIG)
        _, rows = load_catalog(resolve_catalog_path(CONFIG, config))
        self.assertEqual(23, len(rows))

    def test_focus_set_keeps_declared_order(self) -> None:
        _, rows, config = select_policy_rows(CONFIG, "institution_and_foreign_policy")
        actual = [row["policy_id"] for row in rows]
        expected = config["sets"]["institution_and_foreign_policy"]["policy_ids"]
        self.assertEqual(expected, actual)
        self.assertEqual(9, len(actual))

    def test_default_set_contains_every_catalog_policy(self) -> None:
        config = load_config(CONFIG)
        _, rows, _ = select_policy_rows(CONFIG, config["default_set"])
        self.assertEqual(23, len(rows))

    def test_unknown_set_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown policy set"):
            select_policy_rows(CONFIG, "not-a-real-set")


if __name__ == "__main__":
    unittest.main()
