# RiskClock

**Consensus-backed adaptive execution friction for GenLayer Intelligent Contracts.**

RiskClock is a standalone GenLayer Intelligent Contract primitive plus one minimal consumer contract. There is **no frontend** and none is planned — the submission is the primitive and the proof that a second contract can rely on it.

## 1. What RiskClock uniquely does

Most systems give every allowed action the same governance friction: a label edit and an admin transfer both go through "the approval flow." RiskClock answers a narrower, more reusable question instead: **how much execution friction (delay, approval count) must surround this exact, frozen action before another contract may perform it?** It is not a policy-decision engine and does not claim an action is safe — it classifies bounded risk and deterministically converts that classification into friction.

## 2. Why semantic consensus is genuinely required

A traditional contract can enforce a fixed delay or signature threshold, but it cannot tell whether "replace the admin key" and "increment a demo counter" deserve the same friction — that requires reading and weighing the *meaning* of a natural-language action against a charter, which is exactly the class of judgment GenLayer's LLM-backed consensus exists for. A single centralized operator assigning that judgment would defeat the point: the friction schedule is only trustworthy if independent validators, not one party, agree the classification is defensible.

## 3. What the LLM decides

The LLM proposes exactly one thing: a bounded semantic risk vector, four dimensions on a fixed 0..3 scale, for the one frozen action in front of it:

- **reversibility** — how hard is this to undo?
- **privilege expansion** — how much new authority does it grant?
- **external effect** — how far does the consequence reach outside this system?
- **recovery difficulty** — how hard is recovery if it goes wrong?

The LLM never decides whether the action executes, how many approvals are required, the numeric value-risk band, whether any hash matches, or authorization.

## 4. What deterministic code decides

Everything downstream of the semantic vector is pure contract arithmetic, with no model input:

- **value-at-risk** — derived only from the action's numeric `value` against the policy's frozen thresholds; the model cannot influence it;
- the **weighted score** (fixed per-dimension weights × levels);
- the **tier** (LOW/MEDIUM/HIGH/CRITICAL) from the policy's frozen score thresholds;
- the **delay** and **approval count** the tier requires, from the same frozen policy;
- action/policy hash binding, approver whitelisting, replay protection, pause and revocation semantics.

## 5. How validators substantively verify the result

`assess_action` calls `gl.vm.run_nondet_unsafe(observe, validate)`. On live GenVM, the leader's result reaches `validate()` wrapped in `gl.vm.Return` — `validate()` must check `isinstance(leader_result, gl.vm.Return)` and read `leader_result.calldata` before touching it; treating it as a plain dict (an earlier bug in this repository) silently rejects every leader result. See `docs/ARCHITECTURE.md` for the concrete incident.

Once unwrapped, the validator does not just check JSON shape. For a genuine (`SUBSTANTIVE`) leader claim, it independently re-runs the same frozen prompt, recomputes the deterministic tier from its own semantic reading, and requires the **same tier** and **no more than one level of variance per dimension** — real disagreement is rejected, not merely malformed JSON. Live consensus disagreements observed while operating this contract on Studionet were later traced to the `gl.vm.Return` handling bug above, not model unreliability; see `deployments/studionet.json` for that investigation's evidence.

## 6. How failure/non-decision works

A model or infrastructure failure is not a risk judgment and must never be treated like one. RiskClock distinguishes three assessment outcomes:

- `SUBSTANTIVE` — a real, validated semantic classification. Only this can move an action to `ASSESSED`.
- `MODEL_OUTPUT_INVALID` — the assessor's output could not be parsed into the fixed protocol shape. Both leader and validator independently re-derive this deterministically from the same raw text.
- `SOURCE_UNAVAILABLE` — the model call itself failed (exception, timeout, etc.).

Either non-decision increments `assessment_attempts`, records `last_assessment_result`, and leaves the action `PENDING` and non-executable — never a synthesized worst-case verdict, never `ASSESSED`. After `MAX_ASSESSMENT_ATTEMPTS` (12) consecutive non-decisions, the action moves to the terminal `ASSESS_EXHAUSTED` state, still permanently non-executable. The same immutable action can be retried at any point before that.

## 7. How another contract consumes RiskClock

`contracts/riskclock_executor.py` is a second, independent Intelligent Contract exposing one deliberately boring operation, `INCREMENT_COUNTER`. It executes only when it has independently verified:

- the action targets its immutable `target_ref` and exact `operation`;
- the payload hash binds the exact amount being applied;
- the caller-supplied action hash and policy hash match RiskClock's own records for that action (this also binds `action_id`, `proposer`, and `intended_executor` — see below);
- if the action bound a non-zero `intended_executor`, the caller is that address — RiskClock's `is_executable() == true` is a friction-satisfied signal, not a blanket authorization grant, and the consumer enforces that boundary explicitly;
- `RiskClock.is_executable()` is true (active policy, hash match, delay elapsed, approvals met, not revoked);
- this exact action has never executed here before (`action_hash` is globally unique per submission, so two independently authorized actions with identical business fields never collide in the replay map).

## 8. Where the live deployment evidence is

`deployments/studionet.json` is the machine-readable record of the current deployment: addresses, source hashes, the commit SHA, every deployment and lifecycle transaction hash, and — case by case — which parts of the live test plan were completed versus honestly not completed in this session. `BUILD_STATUS.md` carries the same story in prose. Nothing is claimed there that was not personally executed and verified against Studionet chain 61999.

## Network lock

- **Studionet**, chain ID **61999**
- RPC `https://studio.genlayer.com/api`
- GenLayer CLI **0.39.1**

Do not migrate to Studio Next / Studionet-dev / Bradbury or chain 61997.

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
  "score_thresholds": { "medium": 200, "high": 500, "critical": 900 },
  "value_thresholds": { "medium": 100, "high": 1000, "critical": 10000 },
  "delays": { "low": 0, "medium": 60, "high": 3600, "critical": 86400 },
  "approvals": { "low": 0, "medium": 1, "high": 2, "critical": 2 }
}
```

Policy creation is draft-first: create, add approvers, then seal. Once sealed, the definition hash is immutable; the owner may pause/reactivate it, or individually revoke one already-assessed action (distinct from a policy-wide pause — see `docs/SECURITY_MODEL.md`).

## Action lifecycle

```text
PENDING --assess (non-decision)--> PENDING (assessment_attempts += 1)
PENDING --assess (non-decision, attempts == cap)--> ASSESS_EXHAUSTED (terminal)
PENDING --assess (SUBSTANTIVE, validated)--> ASSESSED
PENDING --cancel (proposer/owner)--> CANCELLED
ASSESSED --revoke (policy owner)--> REVOKED (permanent, survives policy reactivation)
```

`is_executable()` is true only for `ASSESSED` actions with matching hashes, an active sealed policy, enough approvals, and an elapsed delay.

## Repository map

- `contracts/riskclock.py` — main primitive
- `contracts/riskclock_executor.py` — minimal consumer
- `tests/direct/` — GenLayer Direct Mode tests (consensus, non-decisions, policy/action/approval edges)
- `tests/unit/` — deterministic reference-model tests
- `reference/risk_model.py` — pure-Python policy math reference
- `scripts/preflight.py` — repository/network/static gate
- `scripts/check_cli.py` — enforces CLI 0.39.1
- `scripts/verify_studionet.py` — verifies chain ID 61999
- `scripts/deploy_studionet.py` — stable-Studionet core deploy helper
- `docs/` — architecture, security model, deployment, live test plan
- `deployments/studionet.json` — the live deployment/lifecycle evidence record

## Local checks

```bash
python -m unittest discover -s tests/unit -p 'test_*.py'
python scripts/preflight.py
python scripts/preflight.py --final   # requires deployments/studionet.json
```

For Direct Mode (installs the pinned `genlayer-test` dependency):

```bash
python -m pip install -r requirements-test.txt
pytest -q tests/direct
```

## Status

See `BUILD_STATUS.md` and `deployments/studionet.json` for the current, single source of truth on what has been deployed, tested, and verified live.
