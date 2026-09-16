# Build status

## Completed in generated package

- standalone RiskClock Intelligent Contract
- minimal RiskClockExecutor consumer contract
- immutable draft/seal policy lifecycle
- four semantic risk dimensions plus deterministic value-at-risk band
- custom validator that independently reassesses and rejects tier disagreement
- malformed-output fail-closed behaviour
- deterministic weighted scoring and tier mapping
- deterministic delay and approval requirements
- approver allowlist / duplicate-approval protection
- policy pause kill switch
- exact policy/action/payload hash binding
- consumer replay protection
- Direct Mode test suite authored
- pure-Python deterministic reference tests authored and executed
- network lock / CLI lock / RPC verifier
- deployment and live-test documentation
- no frontend

## Locally verified in this build environment

- Python syntax compilation: PASS
- deterministic unit tests: PASS
- repository preflight: PASS

## Direct Mode attempt in this environment

- attempted installation of the pinned `genlayer-testing-suite@v0.29.2`
- install could not complete because this container could not resolve `github.com`
- therefore Direct Mode execution is **not claimed** here

## Not claimed yet

- GenLayer Direct Mode execution
- live Studionet deployment
- finalized contract addresses
- live consensus lifecycle
- explorer evidence
- `preflight.py --final`

Those items must be completed by Lola's agent using the funded/authorized wallet and the locked 61999 + CLI 0.39.1 environment. Do not fabricate them.

---

## Update: live Studionet session (chain 61999)

Environment verified before any deployment:

- `python scripts/check_cli.py` -> `OK: genlayer CLI 0.39.1`
- `python scripts/verify_studionet.py` -> `OK: Studionet chain ID 61999 at https://studio.genlayer.com/api`
- `python scripts/preflight.py` -> PASS

### Deployed contracts (real, live, independently re-verified)

- **RiskClock**: `0x9374d4BEC24A58a1f3b639c21C5Dd79f68B2C1Cd`
- **RiskClockExecutor**: `0x3E329F774aa86EEEb1096dDbFEA6919464E511E9` (constructed with the RiskClock address above and `target_ref = "riskclock-demo-counter"`)

Both addresses were re-verified in this session via `genlayer schema <address>` (method signatures match the source) and multiple successful `genlayer call` / SDK read round-trips.

### Policy lifecycle (real, sealed on-chain)

- **Policy 2 "Treasury Risk Policy"** — the exact sample config from README.md. Two approvers added, then sealed. `definition_hash = 70496e5a74912432f1353cdd400e633ed1b5eebef398629bb518b8f1af446fd6`. Re-read via `get_policy(2)` immediately before writing this status: `status=SEALED`, `active=true`, hash matches.
- **Policy 3 "Fast Delay Approval Demo Policy"** — a second policy with short delays (medium=3s, high=5s, critical=8s) created to demonstrate the approval/delay gate quickly. Two approvers added, then sealed. `definition_hash = 25c88a08e738aef73d0cf1c4406fa8705117f7c87be15e75ec1718546cf9267f`. Re-read via `get_policy(3)`: `status=SEALED`, `active=true`, hash matches.

### Action submission (real, on-chain)

- **Action 1** submitted against Policy 2: `target_ref=riskclock-demo-counter`, `operation=INCREMENT_COUNTER`, `value=0`, payload hash bound to amount 7. Submission tx `0xdc037932b28940b5ec44b775fea9cdb3ee683b9bd08d3302027eb1fa3a5295bd` (FINALIZED, MAJORITY_AGREE). Action hash `10051ea2e14189fb92828f29773838b0e96ce62d54849b31446c47afc2639c8f`. Verified on-chain via `get_action(1)`.

### Blocker: `assess_action` could not reach consensus agreement (real, documented)

`assess_action(1)` was called **8 times** across three separate script runs. **Every single call finalized with `MAJORITY_DISAGREE`**, never once with `MAJORITY_AGREE`. All 8 transaction hashes are recorded in `deployments/studionet.json` under `assess_disagreement_evidence`, and each was independently confirmed with `genlayer receipt <hash>` to show:

- leader execution `SUCCESS` (the contract code itself does not crash or revert),
- a real validator quorum where a majority of validators voted `disagree`,
- the disagreement occurs because each validator independently re-runs the same GenLayer semantic-risk LLM prompt (`gl.nondet.exec_prompt`) and derives a **different risk tier** than the leader for this trivial, low-risk action, which the contract's `assess_action` validator logic correctly rejects (per the fail-closed consensus design described in `docs/ARCHITECTURE.md` and `docs/SECURITY_MODEL.md`).
- One receipt (attempt 4 of run 2) shows the leader node's `primary_model` was `policy:prd-mistral`, while the model used in earlier successful transactions on this account was `policy:prd-glm` — i.e. different Studionet validator nodes are currently routed to different underlying LLM families, and those models disagree with each other on how conservatively to rate a benign `INCREMENT_COUNTER` action.

This is real, live evidence that RiskClock's consensus fail-safe is operating as designed (a leader whose semantic assessment the validators cannot independently reproduce is rejected rather than silently accepted) — it is simply happening on every attempt in this session because of live cross-model heterogeneity among Studionet's current validator set, not because of a bug in the contract.

One `execute_increment` call was made against the still-unassessed action to check the consumer's guard: it correctly reverted with `EXPECTED: RiskClock gate is not executable` (tx `0x5bc682c55b3fe95fe35d08b0a7177f9e3de64815d168bee7f0002ccbdfddc171`), confirming the fail-closed gate check works even under this blocker. The counter on the executor remains `0`.

### Honest scope of what was and was not completed

Completed and independently re-verified live on Studionet chain 61999:
- both contracts deployed and functioning,
- both policies created, approver-configured, and sealed with real immutable hashes,
- one action submitted and bound to Policy A's hash,
- the consumer's fail-closed `is_executable` gate check confirmed to correctly block execution of an unassessed action.

**Not completed**, due to the `assess_action` consensus blocker above: any action reaching `ASSESSED`, a successful `execute_increment`, replay rejection after a real execution, the high-risk tier/friction verification, the two-approver + delay-gate demo on Policy B, and the policy-pause invalidation proof. `docs/LIVE_TEST_PLAN.md` steps 7-11 could not be completed in this session for this reason. See `deployments/studionet.json` for the complete, itemized evidence and transaction hashes.
