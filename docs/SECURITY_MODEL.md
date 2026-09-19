# Security model

## Guarantees

- Policy configuration becomes immutable when sealed.
- An action binds `action_id`, policy hash, `proposer`, `intended_executor`, target reference, operation, numeric value, payload hash, and purpose into one action hash — every field a downstream consumer relies on for identity or authorization is cryptographically pinned, not trusted separately.
- `action_id` makes every submission globally unique, so two independently submitted actions with byte-identical business fields never collide in a downstream replay-protection map.
- Numeric value risk is deterministic and cannot be lowered (or raised) by the model.
- Semantic model output is bounded to integers 0..3; a leader result that is not a `gl.vm.Return`, or whose content cannot be parsed, is never treated as a substantive verdict.
- A model/infrastructure failure to produce a usable assessment (`MODEL_OUTPUT_INVALID`, `SOURCE_UNAVAILABLE`) is a retryable non-decision: it is recorded (`assessment_attempts`, `last_assessment_result`) but never sets a risk tier, never sets `assessed_at`, and can never make `is_executable()` return true. It is explicitly not the same protocol outcome as "this action is extremely risky."
- Validators independently reassess substantive semantics; a materially different derived tier rejects consensus.
- Delay and approval requirements are deterministic consequences of the accepted risk vector.
- Only configured approvers can approve, an address cannot approve twice, and the zero address can never be registered as an approver.
- A paused policy makes every associated gate non-executable.
- An individually revoked action is permanently non-executable, even if its policy is later reactivated — a policy-wide pause and an individual revocation are deliberately distinct mechanisms with distinct authorization (policy owner for both, but revocation cannot be undone by reactivating the policy).
- `RiskClock.is_executable()` reports friction satisfaction, not authorization. A consumer that cares who may act on an action must check the bound `intended_executor` itself; `RiskClockExecutor` does this and rejects any other caller when a non-zero `intended_executor` was bound at submission.
- Consumer replay is blocked by `action_hash`, which is unique per submission (see action identity above).

## Non-guarantees

RiskClock does not prove an action will succeed, does not verify the truth of arbitrary prose in `purpose`, does not provide legal/compliance advice, and does not execute arbitrary external actions. A policy owner can intentionally configure weak thresholds; downstream contracts must pin the policy hash they trust. "LOW tier, zero approvals, zero delay" is a friction outcome, not an authorization grant — a consumer that needs an authorization boundary must use `intended_executor` (or an equivalent mechanism) rather than assume RiskClock's friction gate implies it.

## Prompt/data boundary

Action text is explicitly treated as data. It cannot override the fixed protocol dimension definitions. The optional semantic charter is part of the policy definition and therefore intentionally influences interpretation; changing it requires a new policy because sealed policies are immutable.

## Fail-closed choices

- leader result is not a `gl.vm.Return` -> validator rejects (no consensus, no state change)
- leader/validator outcome-type mismatch (e.g. one saw a real answer, the other a non-decision) -> reject
- model output cannot be parsed -> `MODEL_OUTPUT_INVALID` non-decision, action stays PENDING, never executable
- model call itself fails -> `SOURCE_UNAVAILABLE` non-decision, action stays PENDING, never executable
- assessment-attempt cap reached without a substantive result -> `ASSESS_EXHAUSTED`, permanently non-executable
- validator tier disagreement on a genuine substantive claim -> reject
- stale/wrong action or policy hash -> `is_executable()` false
- paused policy -> false
- revoked action -> false, permanently, independent of policy `active` state
- insufficient approvals -> false
- delay not elapsed -> false
- wrong `intended_executor` calling the consumer -> consumer rejects before ever asking RiskClock
