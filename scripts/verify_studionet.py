#!/usr/bin/env python3
"""Fail closed unless the configured RPC reports chain ID 61999."""
from __future__ import annotations
import json
import sys
import urllib.request

RPC = "https://studio.genlayer.com/api"
EXPECTED = 61999


def rpc(method: str):
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": []}).encode()
    request = urllib.request.Request(
        RPC,
        data=body,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (compatible; RiskClockPreflight/1.0)",
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        value = json.loads(response.read().decode())
    if "error" in value:
        raise RuntimeError(value["error"])
    return value.get("result")


def main() -> int:
    try:
        raw = rpc("eth_chainId")
        actual = int(str(raw), 16) if isinstance(raw, str) and raw.startswith("0x") else int(raw)
    except Exception as error:
        print(f"ERROR: could not verify {RPC}: {error}", file=sys.stderr)
        return 2
    if actual != EXPECTED:
        print(f"ERROR: wrong chain. Expected {EXPECTED}, RPC reports {actual}", file=sys.stderr)
        return 3
    print(f"OK: Studionet chain ID {actual} at {RPC}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
