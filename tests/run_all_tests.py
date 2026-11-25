"""Run all tests and print a summary.

Usage:
    python tests/run_all_tests.py

Exit code: 0 if all tests pass, 1 if any fail.
"""

from __future__ import annotations

import os
import sys
import unittest

TEST_MODULES = [
    "tests.test_gesture_engine",
    "tests.test_protocol",
    "tests.test_crc",
    "tests.test_sync_detector",
    "tests.test_integration",
]


def main() -> int:
    # Ensure the workspace root is on sys.path
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if root not in sys.path:
        sys.path.insert(0, root)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    for module_name in TEST_MODULES:
        try:
            module = __import__(module_name, fromlist=["*"])
            suite.addTests(loader.loadTestsFromModule(module))
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR loading {module_name}: {exc}")
            return 1

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    total = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    passed = total - failures - errors

    print("\n" + "=" * 60)
    print(f"Tests run: {total}")
    print(f"Passed:    {passed}")
    print(f"Failures:  {failures}")
    print(f"Errors:    {errors}")
    print("=" * 60)

    if result.wasSuccessful():
        print("ALL TESTS PASSED")
        return 0
    print("SOME TESTS FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
