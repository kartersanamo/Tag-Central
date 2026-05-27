#!/usr/bin/env python3
"""CLI helper script to run all unit tests."""

from __future__ import annotations

import sys
import time
import unittest


def main() -> int:
    """Runs all tests with verbose output and summary."""
    start_time = time.perf_counter()
    loader = unittest.TestLoader()
    suite = loader.discover("tests", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    elapsed = time.perf_counter() - start_time

    print("\n=== Test Run Summary ===")
    print(f"Executed: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors:   {len(result.errors)}")
    print(f"Skipped:  {len(result.skipped)}")
    print(f"Elapsed:  {elapsed:.3f}s")
    print(f"Result:   {'PASS' if result.wasSuccessful() else 'FAIL'}")

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
