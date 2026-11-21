from __future__ import annotations

import argparse
import json
import platform
import sys
import time
import unittest
from pathlib import Path


class JsonResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.rows = []
        self._started = {}

    def startTest(self, test):
        self._started[test.id()] = time.monotonic()
        super().startTest(test)

    def addSuccess(self, test):
        super().addSuccess(test)
        self.rows.append(
            {
                "test": test.id(),
                "status": "passed",
                "seconds": round(time.monotonic() - self._started[test.id()], 3),
            }
        )

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.rows.append(
            {
                "test": test.id(),
                "status": "failed",
                "seconds": round(time.monotonic() - self._started[test.id()], 3),
                "message": self._exc_info_to_string(err, test),
            }
        )

    def addError(self, test, err):
        super().addError(test, err)
        self.rows.append(
            {
                "test": test.id(),
                "status": "error",
                "seconds": round(time.monotonic() - self._started[test.id()], 3),
                "message": self._exc_info_to_string(err, test),
            }
        )

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.rows.append(
            {
                "test": test.id(),
                "status": "skipped",
                "seconds": round(time.monotonic() - self._started[test.id()], 3),
                "message": reason,
            }
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "test-results.json",
    )
    args = parser.parse_args(argv)
    suite = unittest.defaultTestLoader.discover(str(Path(__file__).resolve().parent))
    stream = sys.stdout
    runner = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=JsonResult)
    started = time.time()
    result = runner.run(suite)
    report = {
        "schema": 1,
        "scope": "local control tests only; no phone, fastboot device, or charging hardware access",
        "python": platform.python_version(),
        "platform": platform.platform(),
        "started_unix": round(started, 3),
        "duration_seconds": round(time.time() - started, 3),
        "ran": result.testsRun,
        "passed": result.wasSuccessful(),
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "tests": result.rows,
        "high_voltage_accessed": False,
        "phone_accessed": False,
        "device_rebooted": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, sort_keys=True))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
