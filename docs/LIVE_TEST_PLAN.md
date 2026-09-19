# 61999 live test plan

Do not run this against 61997. Network lock: **Studionet, chain ID 61999, RPC `https://studio.genlayer.com/api`, CLI 0.39.1**.

1. Run `python scripts/preflight.py`, `python scripts/check_cli.py` (expect `0.39.1`), `python scripts/verify_studionet.py` (expect `61999`).
2. Deploy `contracts/riskclock.py`, then `contracts/riskclock_executor.py` with constructor `(RISK_CLOCK_ADDRESS, "riskclock-demo-counter")`. Verify `genlayer schema <address>` matches source for both.
3. Create Policy A with the sample config from README, two approvers, seal it.
4. **Case A — low-risk success**: submit a low-risk `INCREMENT_COUNTER` action (payload hash bound to amount 7). Assess it; require the outcome be `SUBSTANTIVE` and the tier `LOW` with zero delay/approvals. Execute through the consumer; verify the counter advanced by exactly 7.
5. **Case B — replay**: attempt to execute the exact same action again; verify it is rejected and the counter does not advance again.
6. **Case G — hash/policy binding**: call `is_executable` with a wrong action hash and with a wrong policy hash; both must return false.
7. **Case C — high/critical friction**: create Policy B with short delays for a fast live demo. Submit a high-value action that deterministically reaches CRITICAL (value ≥ the critical value threshold) or otherwise requires ≥1 approval. Assess it. Attempt approval from a non-approver and verify rejection. Collect the required distinct approvals from real approvers, verifying `is_executable` stays false until the threshold is met. Verify it also stays false until the configured delay elapses. Execute once every deterministic condition is satisfied; verify the counter advanced.
8. **Case D — pause**: on a separate assessed, executable action, pause its policy and verify `is_executable` becomes false and consumer execution fails; then reactivate the policy for later cases.
9. **Case F — revocation**: assess a fresh action, revoke it as the policy owner, verify it is permanently non-executable, and verify that pausing and reactivating the policy again does not resurrect it.
10. **Case E — retryable non-decision**: exercised in GenLayer Direct Mode (`tests/direct/test_riskclock.py`), which can deterministically force a malformed model response (`MODEL_OUTPUT_INVALID`) or a raised model-call exception (`SOURCE_UNAVAILABLE`) via mocks — something the live network cannot be made to reproduce on demand. Direct Mode proves: the attempt is recorded, the action never becomes executable, and a subsequent real assessment on the same immutable action can still succeed. This is simulated evidence, clearly distinguished from the live cases above; do not present it as live chain evidence.
11. Record every deployed address, transaction hash, consensus outcome, and final read-back state in `deployments/studionet.json` and `BUILD_STATUS.md`.
12. Run `python scripts/preflight.py --final` only after the evidence file reflects real, current-source deployment evidence.

Never invent live evidence. If a live call fails for a reason other than expected consensus variance, document the failure with its transaction hash and leave the final status honestly incomplete rather than substituting a plausible-sounding claim.
