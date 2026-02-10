"""Helpers for loading environment variables from a .env file."""

from __future__ import annotations

import os
from typing import Optional


def load_env_file(path: Optional[str]) -> None:
    """Load environment variables from a simple .env file.

    Lines are expected to be KEY=VALUE. Empty lines and lines starting with '#'
    are ignored. Surrounding quotes around values are stripped.
    """
    if not path:
        return
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError as exc:
        raise RuntimeError(f"Failed to read env file at {path}: {exc}") from exc
