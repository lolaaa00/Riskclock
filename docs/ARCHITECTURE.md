# RiskClock architecture

RiskClock is a standalone GenLayer primitive for **adaptive execution friction**. It does not decide whether an action is morally or operationally good. It classifies bounded risk dimensions under consensus, then deterministic contract logic maps that vector into a delay and approval threshold.

## State machine

`RiskPolicy: DRAFT -> SEALED`, with a reversible operational `active` flag after sealing.

`Action: PENDING -> ASSESSED`; only `PENDING -> CANCELLED` is allowed. Assessed actions are immutable. Pausing the policy can invalidate all gates without rewriting history.

## Risk model

Four dimensions are semantic and assessed by GenLayer validators on a 0..3 scale: reversibility, privilege expansion, external effect, and recovery difficulty. `value_at_risk` is **not** LLM-derived. It is deterministically mapped from the numeric `value` through policy thresholds.

The five levels are multiplied by immutable weights. Score thresholds deterministically select LOW, MEDIUM, HIGH, or CRITICAL. Each tier maps to an immutable delay and approval count.

## Consensus boundary

The leader proposes the four semantic levels. A validator independently re-runs the assessment. Validation requires the same resulting risk tier and no semantic dimension may differ by more than one level. This makes the consensus target the execution consequence instead of superficial JSON equality.

Malformed model output fails maximally closed: all semantic dimensions become level 3.

## Composability

`is_executable(action_id, action_hash, policy_hash)` returns true only when the policy remains active, the immutable hashes match, the action is assessed, the delay has elapsed, and the approval threshold is satisfied.

`RiskClockExecutor` is a minimal second contract. It verifies the exact operation and payload hash, checks RiskClock, prevents replay, then mutates its own counter. It exists solely to prove the primitive can gate another Intelligent Contract without turning RiskClock into a frontend/product.
