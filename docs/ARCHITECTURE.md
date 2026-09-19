# RiskClock architecture

RiskClock is a standalone GenLayer primitive for **adaptive execution friction**. It does not decide whether an action is morally or operationally good. It classifies bounded risk dimensions under consensus, then deterministic contract logic maps that vector into a delay and approval threshold.

## State machine

`RiskPolicy: DRAFT -> SEALED`, with a reversible operational `active` flag after sealing.

`Action: PENDING -> ASSESSED`, `PENDING -> CANCELLED`, `PENDING -> ASSESS_EXHAUSTED` (terminal, after `MAX_ASSESSMENT_ATTEMPTS` consecutive non-decisions), `ASSESSED -> REVOKED` (policy owner only, permanent). A non-decision assessment attempt (see below) leaves an action `PENDING`; it is not a fifth transition target of its own, just a recorded attempt. Assessed actions' risk fields are immutable once set. Pausing the policy invalidates all of its gates operationally without rewriting history; revoking one action invalidates just that action, permanently, independent of policy state.

## Risk model

Four dimensions are semantic and assessed by GenLayer validators on a 0..3 scale: reversibility, privilege expansion, external effect, and recovery difficulty. `value_at_risk` is **not** LLM-derived. It is deterministically mapped from the numeric `value` through policy thresholds.

The five levels are multiplied by immutable weights. Score thresholds deterministically select LOW, MEDIUM, HIGH, or CRITICAL. Each tier maps to an immutable delay and approval count.

## Consensus boundary and the `gl.vm.Return` incident

`assess_action` calls `gl.vm.run_nondet_unsafe(observe, validate)`. On live GenVM, the leader's result reaches `validate(leader_result)` wrapped in a `gl.vm.Return` object (`leader_result.calldata` holds the actual value) — this is a documented runtime contract, confirmed against the GenLayer SDK source (`genlayer/gl/vm.py`, `Return` dataclass) and the official `genlayer-project-boilerplate` example contract, which uses exactly `isinstance(leader_result, glvm.Return)` before touching it.

An earlier version of this contract's `validate()` treated `leader_result` as a plain dict and indexed into it directly. On live Studionet this silently rejected every leader proposal: the plain-dict assumption doesn't hold outside GenLayer Direct Mode's local test shim (which, unlike real GenVM, calls the leader function directly without wrapping it unless a test explicitly replays the validator via `direct_vm.run_validator()`). The result was eight consecutive `MAJORITY_DISAGREE` outcomes recorded against the prior deployment, at the time attributed to cross-model heterogeneity among validator nodes. That attribution has been superseded: the validator function itself was broken and would reject *any* leader result, valid or not, regardless of model. See `deployments/studionet.json` for both the old (superseded) evidence and the corrected contract's live results.

The validator now:

1. Rejects anything that is not a `gl.vm.Return` (a leader that raised, or a malformed wrapper).
2. Reads `leader = leader_result.calldata` and checks it carries a recognized `outcome`.
3. Independently computes its own `follower = observe()`.
4. Requires `leader["outcome"] == follower["outcome"]` — the two independent observations must agree on *what kind* of result occurred before either is trusted further.
5. For a non-decision outcome (`MODEL_OUTPUT_INVALID` / `SOURCE_UNAVAILABLE`), outcome-type agreement is itself sufficient: both leader and validator independently reached the same non-decision from their own model calls, which is a deterministic, checkable fact, not a subjective judgement.
6. For a `SUBSTANTIVE` outcome, the validator additionally requires the same derived risk tier and at most one level of variance per semantic dimension between leader and follower — this is the actual, substantive judgement check, not shape validation.

## Assessment outcomes and non-decisions

`_observe()` never raises past its own boundary. It converts every failure mode into one of three explicit outcomes:

- `SUBSTANTIVE` — a real classification, only this can produce `ASSESSED`.
- `MODEL_OUTPUT_INVALID` — the assessor responded, but its output could not be parsed into the fixed protocol shape.
- `SOURCE_UNAVAILABLE` — the model call itself raised (timeout, infra failure, etc.).

`assess_action` records every attempt: `assessment_attempts` increments unconditionally, and `last_assessment_result` is always updated. Only a `SUBSTANTIVE`, validated outcome ever sets `assessed_at`, the risk vector, tier, delay, or approval requirement, or moves status to `ASSESSED`. A non-decision leaves every one of those fields untouched and the action `PENDING`, unless the attempt cap is reached, in which case status becomes the terminal `ASSESS_EXHAUSTED` — still permanently non-executable, distinguishable in `get_action()` from both a real low-risk approval and a cancellation.

## Authorization boundary

RiskClock answers a friction question, not an authorization question, but the two must not be conflated. Every action optionally binds an `intended_executor` address at submission time (the zero address means "unrestricted"), and that value is cryptographically bound into the action's hash alongside `action_id`, `proposer`, `policy_id`/`policy_hash`, `target_ref`, `operation`, `value`, `payload_hash`, and `purpose`. `is_executable()` reports whether an action's friction requirements are satisfied; it deliberately says nothing about *who* may act on that. A downstream consumer that cares about actor identity must check `intended_executor` itself — `RiskClockExecutor` does exactly this, rejecting any caller other than the bound `intended_executor` when one was specified.

## Action identity and replay

`action_id` (a RiskClock-global, monotonically increasing counter) is bound into the action hash specifically so that two independently submitted actions with byte-identical business fields (same target, operation, value, payload, purpose) never produce the same hash. This makes every submission an independent, separately executable instance, and it means a downstream consumer's replay-protection map — keyed by `action_hash`, as `RiskClockExecutor.executions` is — can never conflate two distinct authorized actions into one. Replay of the *same* action is still blocked by that same map.

## Composability

`is_executable(action_id, action_hash, policy_hash)` returns true only when the action is `ASSESSED` (never for `PENDING`, `CANCELLED`, `REVOKED`, or `ASSESS_EXHAUSTED`), the immutable hashes match, the policy remains active and sealed, the approval threshold is satisfied, and the delay has elapsed.

`RiskClockExecutor` is a minimal second contract. It independently verifies target, operation, payload hash, both bound hashes, the `intended_executor` boundary, and replay, then checks `is_executable()` before mutating its own state. It exists solely to prove the primitive can gate another Intelligent Contract without turning RiskClock into a frontend/product.
