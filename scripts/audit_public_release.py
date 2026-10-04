#!/usr/bin/env python3
"""Fail when a prospective public snapshot contains private or mirrored data."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Iterable


PRIVATE_PREFIXES = ("data/private/", "outputs/", "backups/")
ALLOWED_SOURCE_NAMES = {"README.md"}
DUMMY_SECRET_VALUES = {"dummy", "example", "from-file", "test", "value"}
TOKEN_PATTERN = re.compile(
    r"X_API_BEARER_TOKEN[ \t]*=[ \t]*([A-Za-z0-9%._~-]{20,})"
)
PRIVATE_KEY_MARKER = "-----BEGIN " + "PRIVATE KEY-----"


def candidate_paths(root: Path) -> list[Path]:
    if (root / ".git").exists():
        result = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
        paths = [Path(name) for name in result.stdout.split("\0") if name]
        return [path for path in paths if (root / path).is_file()]
    return [
        path.relative_to(root)
        for path in root.rglob("*")
        if path.is_file() and ".git" not in path.parts
    ]


def audit_paths(root: Path, paths: Iterable[Path]) -> list[str]:
    errors: list[str] = []
    relative_paths = sorted({path.as_posix() for path in paths})
    if "LICENSE" not in relative_paths:
        errors.append("LICENSE is missing")
    if "THIRD_PARTY_NOTICES.md" not in relative_paths:
        errors.append("THIRD_PARTY_NOTICES.md is missing")

    for relative in relative_paths:
        path = Path(relative)
        if relative == ".env" or (
            relative.startswith(".env.") and relative != ".env.example"
        ):
            errors.append(f"secret environment file included: {relative}")
        if any(relative.startswith(prefix) for prefix in PRIVATE_PREFIXES):
            errors.append(f"private path included: {relative}")
        if path.parts and path.parts[0] == "sources" and path.name not in ALLOWED_SOURCE_NAMES:
            errors.append(f"mirrored source file included: {relative}")

        absolute = root / path
        try:
            text = absolute.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if PRIVATE_KEY_MARKER in text:
            errors.append(f"private key marker found: {relative}")
        for match in TOKEN_PATTERN.finditer(text):
            value = match.group(1).strip("'\"")
            if value and value.casefold() not in DUMMY_SECRET_VALUES:
                errors.append(f"nonempty X bearer token found: {relative}")
                break
    return errors


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    errors = audit_paths(root, candidate_paths(root))
    if errors:
        print("公開前監査: NG")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("公開前監査: OK")


if __name__ == "__main__":
    main()
