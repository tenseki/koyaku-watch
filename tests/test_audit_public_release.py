import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from audit_public_release import audit_paths


class AuditPublicReleaseTest(unittest.TestCase):
    def test_safe_snapshot_passes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {
                "LICENSE": "MIT",
                "THIRD_PARTY_NOTICES.md": "notices",
                ".env.example": "X_API_BEARER_TOKEN=\n",
                "sources/example/README.md": "source record",
            }
            for relative, content in files.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            self.assertEqual([], audit_paths(root, map(Path, files)))

    def test_private_and_mirrored_data_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {
                "data/private/posts.csv": "text",
                "sources/example/page.html": "html",
                ".env": (
                    "X_API_BEARER_TOKEN=" + "real-" + "secret-" + "123456789012345"
                ),
            }
            for relative, content in files.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            errors = audit_paths(root, map(Path, files))
            self.assertTrue(any("private path" in error for error in errors))
            self.assertTrue(any("mirrored source" in error for error in errors))
            self.assertTrue(any("bearer token" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
