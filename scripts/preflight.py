#!/usr/bin/env python3
from __future__ import annotations
import argparse
import json
import pathlib
import py_compile
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md",
    "SUBMISSION.md",
    "AGENT_HANDOFF.md",
    "BUILD_STATUS.md",
    "NETWORK_LOCK.json",
    "contracts/riskclock.py",
    "contracts/riskclock_executor.py",
    "docs/ARCHITECTURE.md",
    "docs/SECURITY_MODEL.md",
    "docs/LIVE_TEST_PLAN.md",
]


def fail(message: str) -> None:
    print(f"FAIL: {message}")
    raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--final", action="store_true", help="also require real deployment evidence")
    args = parser.parse_args()

    for rel in REQUIRED:
        if not (ROOT / rel).is_file():
            fail(f"missing {rel}")

    lock = json.loads((ROOT / "NETWORK_LOCK.json").read_text())
    if lock.get("chain_id") != 61999:
        fail("NETWORK_LOCK chain_id must be 61999")
    if lock.get("rpc") != "https://studio.genlayer.com/api":
        fail("NETWORK_LOCK RPC is not stable Studionet")
    if lock.get("genlayer_cli") != "0.39.1":
        fail("CLI lock must be 0.39.1")

    operational = [
        ROOT / "contracts" / "riskclock.py",
        ROOT / "contracts" / "riskclock_executor.py",
        ROOT / "gltest.config.yaml",
        ROOT / "scripts" / "deploy_studionet.py",
        ROOT / "scripts" / "verify_studionet.py",
    ]
    for path in operational:
        text = path.read_text()
        if "61997" in text or "studio-next.genlayer.com" in text:
            fail(f"forbidden 61997/studio-next reference in operational file {path.relative_to(ROOT)}")

    for forbidden in ("package.json", "vite.config.js", "next.config.js"):
        if (ROOT / forbidden).exists():
            fail(f"frontend artifact present: {forbidden}")
    for forbidden_dir in ("src", "app", "frontend", "web"):
        if (ROOT / forbidden_dir).is_dir():
            fail(f"frontend directory present: {forbidden_dir}")

    for rel in ("contracts/riskclock.py", "contracts/riskclock_executor.py", "reference/risk_model.py"):
        try:
            py_compile.compile(str(ROOT / rel), doraise=True)
        except Exception as error:
            fail(f"syntax compile failed for {rel}: {error}")

    main_contract = (ROOT / "contracts" / "riskclock.py").read_text()
    for needle in (
        "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6",
        "gl.vm.run_nondet_unsafe",
        "def is_executable",
        "value_risk_level",
        "approvals_required",
    ):
        if needle not in main_contract:
            fail(f"main contract missing invariant marker: {needle}")

    tests = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests/unit", "-p", "test_*.py"],
        cwd=ROOT,
        check=False,
    )
    if tests.returncode != 0:
        fail("pure deterministic unit tests failed")

    if args.final:
        deployment = ROOT / "deployments" / "studionet.json"
        if not deployment.is_file():
            fail("final mode requires deployments/studionet.json")
        data = json.loads(deployment.read_text())
        if data.get("chain_id") != 61999:
            fail("deployment evidence chain_id is not 61999")
        pattern = re.compile(r"^0x[0-9a-fA-F]{40}$")
        for key in ("riskclock_address", "executor_address"):
            if not pattern.match(str(data.get(key, ""))):
                fail(f"final deployment evidence missing valid {key}")
        if data.get("network") != "studionet":
            fail("deployment evidence network must be studionet")

    print("PASS: RiskClock preflight")
    if not args.final:
        print("NOTE: live deployment evidence is intentionally not required without --final")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
