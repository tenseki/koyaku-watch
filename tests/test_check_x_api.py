import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import check_x_api


class LoadLocalEnvTests(unittest.TestCase):
    def test_loads_token_without_overwriting_existing_environment(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            env_file = Path(temp_dir) / ".env"
            env_file.write_text(
                "# comment\nX_API_BEARER_TOKEN=from-file\nQUOTED='value'\n",
                encoding="utf-8",
            )
            with mock.patch.dict(os.environ, {"X_API_BEARER_TOKEN": "existing"}, clear=True):
                check_x_api.load_local_env(env_file)
                self.assertEqual(os.environ["X_API_BEARER_TOKEN"], "existing")
                self.assertEqual(os.environ["QUOTED"], "value")


class LookupTests(unittest.TestCase):
    @mock.patch("scripts.check_x_api.api_get")
    def test_lookup_user_strips_at_sign(self, api_get):
        api_get.return_value = {"data": {"id": "1", "username": "XDevelopers"}}

        result = check_x_api.lookup_user("@XDevelopers", "secret")

        self.assertEqual(result["id"], "1")
        self.assertEqual(api_get.call_args.args[0], "/users/by/username/XDevelopers")

    @mock.patch("scripts.check_x_api.api_get")
    def test_lookup_post_requests_one_post_by_id(self, api_get):
        api_get.return_value = {"data": {"id": "123", "text": "example"}}

        result = check_x_api.lookup_post("123", "secret")

        self.assertEqual(result["id"], "123")
        self.assertEqual(api_get.call_args.args[0], "/tweets/123")


if __name__ == "__main__":
    unittest.main()
