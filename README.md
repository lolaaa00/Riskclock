# RiskClock

**Consensus-backed adaptive execution friction for GenLayer Intelligent Contracts.**

RiskClock answers a narrower and more reusable question than a policy gate: **how much execution friction must surround this exact action before another contract may perform it?** GenLayer consensus classifies bounded semantic risk. Deterministic contract logic converts that risk into a tier, delay, and approval threshold under an immutable policy.

There is **no frontend**. RiskClock is a standalone contract primitive plus a tiny consumer contract used to prove composability.

## Network lock

This repository is intentionally locked to:

- **Studionet**
- **chain ID 61999**
- RPC `https://studio.genlayer.com/api`
- **GenLayer CLI 0.39.1**

Do not migrate this package to Studio Next / Studionet-dev.

## Why RiskClock exists

Most systems give every allowed action the same governance friction. Updating a label and replacing an administrator can both be “allowed”, but they should not necessarily have the same delay or approval threshold.

RiskClock separates two jobs:

1. GenLayer consensus determines a bounded risk vector for the exact frozen action.
2. Deterministic code maps that vector to the policy's precommitted friction schedule.

The LLM never chooses the delay, number of approvals, numeric value band, or whether hashes match.

## Risk dimensions

Semantic, validator-assessed 0..3:

- reversibility
- privilege expansion
- external effect
- recovery difficulty

Deterministic:

- value at risk, derived from the action's numeric `value` and frozen policy thresholds

## Sample policy config

```json
{
  "weights": {
    "reversibility": 100,
    "privilege_expansion": 100,
    "value_at_risk": 100,
    "external_effect": 100,
    "recovery_difficulty": 100
  },
  "score_thresholds": {
    "medium": 200,
    "high": 500,
    "critical": 900
  },
  "value_thresholds": {
    "medium": 100,
    "high": 1000,
    "critical": 10000
  },
  "delays": {
    "low": 0,
    "medium": 60,
    "high": 3600,
    "critical": 86400
  },
  "approvals": {
    "low": 0,
    "medium": 1,
    "high": 2,
    "critical": 2
  }
}
```

Policy creation is draft-first: create, add approvers, then seal. Once sealed, the policy definition hash is immutable. The owner may pause or reactivate it operationally.

## Action flow

```text
create policy -> add approvers -> seal
                              |
                              v
submit exact action -> PENDING
                              |
                              v
                   GenLayer assessment
                              |
                              v
                         ASSESSED
                              |
                   deterministic mapping
                              |
             +----------------+----------------+
             |                |                |
           delay          approvals       policy active
             |                |                |
             +----------------+----------------+
                              |
                              v
                       is_executable()
                              |
                              v
                    consumer state change
```

Every action hash binds policy ID/hash, target reference, operation, numeric value, payload hash, and purpose. A downstream contract should pin both action hash and policy hash.

## Consensus design

The leader returns only the four semantic 0..3 levels plus an explanation. The contract itself adds deterministic value risk, calculates the weighted score, selects the tier, and looks up delay/approval requirements.

A validator independently repeats the semantic assessment. Validation requires the same derived risk tier and at most one level of variance on each semantic dimension. A tier disagreement rejects the leader. Malformed output becomes maximum semantic risk rather than silently becoming LOW.

This means consensus is about the **execution consequence**, not JSON formatting.

## Consumer proof

`contracts/riskclock_executor.py` exposes one intentionally boring operation: `INCREMENT_COUNTER`. It only executes when:

- the RiskClock action targets its immutable `target_ref`;
- the operation is exactly `INCREMENT_COUNTER`;
- the payload hash binds the exact amount;
- action and policy hashes match;
- RiskClock says the action is executable; and
- the action hash has never executed before.

That keeps the submission a reusable primitive rather than a product app.

## Repository map

- `contracts/riskclock.py` — main primitive
- `contracts/riskclock_executor.py` — minimal consumer
- `tests/direct/` — GenLayer Direct Mode tests
- `tests/unit/` — deterministic reference-model tests
- `reference/risk_model.py` — pure-Python policy math reference
- `scripts/preflight.py` — repository/network/static gate
- `scripts/check_cli.py` — enforces CLI 0.39.1
- `scripts/verify_studionet.py` — verifies chain ID 61999
- `scripts/deploy_studionet.py` — stable-Studionet core deploy helper
- `docs/` — architecture, security and live test plan
- `AGENT_HANDOFF.md` — exact instructions for Lola's agent

## Local checks

```bash
python -m unittest discover -s tests/unit -p 'test_*.py'
python scripts/preflight.py
```

For Direct Mode after installing the pinned test dependency:

```bash
python -m pip install -r requirements-test.txt
pytest -q tests/direct
```

## Honest build status

The generated ZIP has been statically compiled and its pure deterministic tests/preflight run locally. It has **not** been deployed from this environment and Direct Mode is not claimed as run here because the GenLayer test package is not installed in the build container. See `BUILD_STATUS.md`.
