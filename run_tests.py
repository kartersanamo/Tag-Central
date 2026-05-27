#!/usr/bin/env python3
"""CLI helper script to run all unit tests."""

from __future__ import annotations

import subprocess
import sys


def main() -> int:
    """Runs all tests and returns the test process exit code."""
    command = [
        sys.executable,
        "-m",
        "unittest",
        "discover",
        "-s",
        "tests",
        "-p",
        "test_*.py",
    ]
    return subprocess.run(command, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
