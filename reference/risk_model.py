"""Pure-Python reference model for RiskClock's deterministic mechanics.

This module intentionally has no GenLayer dependency. It is used by local CI to
prove the policy math, hashing, and tier mapping independently of GenVM.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

DIMENSIONS = (
    "reversibility",
    "privilege_expansion",
    "value_at_risk",
    "external_effect",
    "recovery_difficulty",
)
SEMANTIC_DIMENSIONS = tuple(x for x in DIMENSIONS if x != "value_at_risk")
TIERS = ("low", "medium", "high", "critical")


def canonical_config(config: dict) -> str:
    required = {"weights", "score_thresholds", "value_thresholds", "delays", "approvals"}
    if set(config) != required:
        raise ValueError("bad top-level keys")
    if set(config["weights"]) != set(DIMENSIONS):
        raise ValueError("bad weights")
    if set(config["score_thresholds"]) != {"medium", "high", "critical"}:
        raise ValueError("bad score thresholds")
    if set(config["value_thresholds"]) != {"medium", "high", "critical"}:
        raise ValueError("bad value thresholds")
    if set(config["delays"]) != set(TIERS) or set(config["approvals"]) != set(TIERS):
        raise ValueError("bad friction map")
    m, h, c = (int(config["score_thresholds"][k]) for k in ("medium", "high", "critical"))
    if not (0 < m < h < c <= 3 * sum(int(v) for v in config["weights"].values())):
        raise ValueError("bad score ordering")
    vm, vh, vc = (int(config["value_thresholds"][k]) for k in ("medium", "high", "critical"))
    if not (0 < vm < vh < vc):
        raise ValueError("bad value ordering")
    ds = [int(config["delays"][k]) for k in TIERS]
    aps = [int(config["approvals"][k]) for k in TIERS]
    if ds != sorted(ds) or aps != sorted(aps):
        raise ValueError("friction must be non-decreasing")
    return json.dumps(config, sort_keys=True, separators=(",", ":"))


def keccak_compat(data: bytes) -> str:
    # Python's stdlib SHA3-256 differs slightly from Ethereum Keccak-256.
    # This helper is only for deterministic local fixture identities. On-chain
    # hashes are produced by GenLayer's Keccak256 implementation.
    return hashlib.sha3_256(data).hexdigest()


def value_level(value: int, config: dict) -> int:
    t = config["value_thresholds"]
    if value >= int(t["critical"]):
        return 3
    if value >= int(t["high"]):
        return 2
    if value >= int(t["medium"]):
        return 1
    return 0


def tier_for(score: int, config: dict) -> str:
    t = config["score_thresholds"]
    if score >= int(t["critical"]):
        return "critical"
    if score >= int(t["high"]):
        return "high"
    if score >= int(t["medium"]):
        return "medium"
    return "low"


def assess(levels: dict, value: int, config: dict) -> dict:
    semantic = {key: int(levels[key]) for key in SEMANTIC_DIMENSIONS}
    if any(v < 0 or v > 3 for v in semantic.values()):
        raise ValueError("levels must be 0..3")
    vl = value_level(value, config)
    all_levels = {**semantic, "value_at_risk": vl}
    score = sum(all_levels[k] * int(config["weights"][k]) for k in DIMENSIONS)
    tier = tier_for(score, config)
    return {
        "levels": all_levels,
        "score": score,
        "tier": tier,
        "delay_seconds": int(config["delays"][tier]),
        "approvals_required": int(config["approvals"][tier]),
    }


def increment_payload_hash(amount: int) -> str:
    payload = json.dumps({"amount": int(amount)}, sort_keys=True, separators=(",", ":"))
    return keccak_compat(payload.encode())
