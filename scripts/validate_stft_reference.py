#!/usr/bin/env python3
"""
Release-style gate: STFT reference tests (Parseval-style energy + bin-aligned partial).

Exit code 0 if all checks pass; non-zero otherwise. Intended for CI or pre-release:

  python scripts/validate_stft_reference.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    tests = ROOT / "tests" / "test_stft_reference_goldens.py"
    if not tests.is_file():
        print("Missing", tests, file=sys.stderr)
        return 2
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        str(tests),
        "-q",
        "--tb=short",
    ]
    return int(subprocess.call(cmd, cwd=str(ROOT)))


if __name__ == "__main__":
    raise SystemExit(main())
