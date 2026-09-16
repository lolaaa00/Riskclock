# Security model

## Guarantees

- Policy configuration becomes immutable when sealed.
- An action binds policy hash, target reference, operation, numeric value, payload hash and purpose into one action hash.
- Numeric value risk is deterministic and cannot be lowered by the model.
- Semantic model output is bounded to integers 0..3; malformed output fails closed.
- Validators independently reassess semantics; a different derived tier rejects consensus.
- Delay and approval requirements are deterministic consequences of the accepted risk vector.
- Only configured approvers can approve, and one address cannot approve twice.
- A paused policy makes every associated gate non-executable.
- Consumer replay is blocked by action hash.

## Non-guarantees

RiskClock does not prove an action will succeed, does not verify the truth of arbitrary prose in `purpose`, does not provide legal/compliance advice, and does not execute arbitrary external actions. A policy owner can intentionally configure weak thresholds; downstream contracts must pin the policy hash they trust.

## Prompt/data boundary

Action text is explicitly treated as data. It cannot override the fixed protocol dimension definitions. The optional semantic charter is part of the policy definition and therefore intentionally influences interpretation; changing it requires a new policy because sealed policies are immutable.

## Fail-closed choices

- malformed LLM output -> maximum semantic risk
- validator tier disagreement -> reject
- stale/wrong policy hash -> false
- paused policy -> false
- insufficient approvals -> false
- delay not elapsed -> false
