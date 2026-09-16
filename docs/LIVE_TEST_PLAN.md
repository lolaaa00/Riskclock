# 61999 live test plan

Do not run this against 61997. Network lock: **Studionet, chain ID 61999, RPC `https://studio.genlayer.com/api`, CLI 0.39.1**.

1. Run `python scripts/preflight.py`.
2. Run `python scripts/check_cli.py` and confirm exactly 0.39.1.
3. Run `python scripts/verify_studionet.py` and confirm 61999.
4. Deploy `contracts/riskclock.py`.
5. Deploy `contracts/riskclock_executor.py` with constructor arguments `(RISK_CLOCK_ADDRESS, "riskclock-demo-counter")`.
6. Create a policy with the sample config from README; add two approvers; seal it.
7. Submit a low-risk `INCREMENT_COUNTER` action whose payload hash binds amount 7. Assess it and verify LOW / zero delay / zero approvals under the sample config. Execute through the consumer and verify counter becomes 7. Replay must fail.
8. Submit a high-risk action using a purpose that clearly expands admin authority and creates difficult-to-reverse external effects. Assess it and verify the resulting tier imposes the deterministic configured friction.
9. For a tier requiring approvals, show non-approver rejection, two distinct approver calls, and gate state before/after threshold.
10. Pause the policy and prove `is_executable` becomes false even for an otherwise-ready action.
11. Record both deployed addresses, tx hashes, policy hash, action hashes, consensus verdicts and explorer links in `deployments/studionet.json` and `BUILD_STATUS.md`.
12. Run `python scripts/preflight.py --final` only after the evidence file is real.

Never invent live evidence. If any call fails, document the failure and leave final status incomplete.
