#!/usr/bin/env python3
from __future__ import annotations
import re
import shutil
import subprocess
import sys

EXPECTED = "0.39.1"


def main() -> int:
    cli = shutil.which("genlayer")
    if cli is None:
        print("ERROR: genlayer CLI not found on PATH", file=sys.stderr)
        return 2
    result = subprocess.run([cli, "--version"], text=True, capture_output=True, check=False)
    text = (result.stdout + "\n" + result.stderr).strip()
    match = re.search(r"(?<!\d)(\d+\.\d+\.\d+)(?!\d)", text)
    if result.returncode != 0 or match is None:
        print(f"ERROR: could not determine CLI version: {text}", file=sys.stderr)
        return 2
    actual = match.group(1)
    if actual != EXPECTED:
        print(f"ERROR: RiskClock requires genlayer CLI {EXPECTED}; found {actual}", file=sys.stderr)
        return 3
    print(f"OK: genlayer CLI {actual}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
