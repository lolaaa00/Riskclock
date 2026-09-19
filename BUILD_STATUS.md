# Build status

**This is the current, single source of truth.** Earlier sections of this file describing an incomplete or blocked build have been superseded and are archived at the bottom for historical context only — do not treat them as current.

## Summary

RiskClock is deployed, tested, and verified live on Studionet (chain 61999). The full lifecycle in `docs/LIVE_TEST_PLAN.md` — low-risk success, replay rejection, hash-binding rejection, high/critical friction with real approvals and a real delay, policy pause, and individual action revocation — has been executed and independently verified on-chain. See `deployments/studionet.json` for the complete, itemized machine-readable record; this file summarizes it in prose.

## What changed from the previous session

1. **Fixed the real consensus validator bug.** `assess_action`'s `validate()` function treated the leader's `run_nondet_unsafe` result as a plain dict. On live GenVM the leader result is wrapped in `gl.vm.Return` (payload in `.calldata`) — confirmed against the GenLayer SDK source and the official `genlayer-project-boilerplate` example. The old code silently rejected every leader proposal. The previous session's 8 recorded `MAJORITY_DISAGREE` transactions were attributed at the time to cross-model validator heterogeneity; that explanation is now disproven. After the fix, the same class of action reached real substantive `MAJORITY_AGREE` consensus **on the first attempt, every time**, in this session.
2. **Replaced synthesized worst-case risk with explicit non-decisions.** A model/infrastructure failure to produce a usable assessment (`MODEL_OUTPUT_INVALID`, `SOURCE_UNAVAILABLE`) is now recorded (`assessment_attempts`, `last_assessment_result`) and leaves the action `PENDING`, never `ASSESSED`, never executable. A cap (`MAX_ASSESSMENT_ATTEMPTS = 12`) moves an action to a terminal `ASSESS_EXHAUSTED` state if no substantive result is ever reached.
3. **Added `revoke_action`.** The policy owner can permanently disable one already-assessed action, distinct from a policy-wide pause; revocation survives a subsequent pause/reactivate cycle.
4. **Bound `action_id`, `proposer`, and `intended_executor` into the action hash.** Two independently submitted actions with byte-identical business fields now get distinct hashes (fixing a replay/identity ambiguity), and a consumer can enforce `intended_executor` as an explicit authorization boundary — `RiskClockExecutor` does this.
5. **Closed edges**: zero-address approvers rejected.
6. **Expanded Direct Mode tests from 10 to 31**, covering the corrected consensus interface, non-decisions and attempt accounting, revocation, action-identity/hash binding, and approval/delay edges. All 31 pass.

## Fresh deployment (chain 61999)

- **RiskClock**: `0xAB3D753dc93c3d29416Ad926f8Ab6212f5ae25ec` (deploy tx `0x0ee11281d02a7fc126569fbd52388cc926da2257510b397305e182e3c685d13d`, `MAJORITY_AGREE`)
- **RiskClockExecutor**: `0x8f96b15FE828356575Ae4Ca6a02A56d4d5723901` (deploy tx `0x9e69b77e7496cbbb2e22e3452388dfcb0a27496b84f7bb173861072e28e2b6f3`, `MAJORITY_AGREE`; constructed with the RiskClock address above and `target_ref = "riskclock-demo-counter"`)

Both re-verified via `genlayer schema <address>` immediately after deployment (method signatures, including `revoke_action` and the `intended_executor` constructor/field, match source exactly).

**Important**: this supersedes the previous session's addresses (`0x9374d4BEC24A58a1f3b639c21C5Dd79f68B2C1Cd` / `0x3E329F774aa86EEEb1096dDbFEA6919464E511E9`), which ran the pre-fix source. Do not use those addresses as evidence for the current contract.

## A second real bug found and fixed during this session

Separately from the contract fix, policy setup (`add_approver`, `seal_policy`) initially reverted on-chain (`AttributeError` in the contract's storage layer) despite the transactions reporting `FINALIZED`/`MAJORITY_AGREE` — validators were agreeing on the *error* outcome, not a success. Root cause: `genlayer_py`'s Python client does not auto-convert a raw address string into its `Address` calldata wrapper; `genlayer_py.types.CalldataAddress(...)` must be used explicitly. This was a bug in the live-testing script, not the contract, but it is exactly the kind of "finalized but actually reverted" trap this project has now hit twice — every write in the evidence below was verified by an independent state read afterward, not merely by its receipt status. See `deployments/studionet.json.pre_fix_reverted_attempts` for the real reverted transaction hashes from before this fix.

## Live lifecycle evidence (real, on-chain, chain 61999)

All of the following were executed live and independently re-verified via `genlayer call` after the fact. Full transaction hashes are in `deployments/studionet.json`.

- **Policy 1 "Treasury Risk Policy"** (sample config from README) and **Policy 2 "Fast Delay Approval Demo Policy"** (short delays: medium 3s / high 5s / critical 8s) — both sealed with real immutable hashes, two approvers each.
- **Case A — low-risk success**: action submitted, assessed `SUBSTANTIVE`/`LOW` on the first consensus attempt, executed through the consumer. Counter advanced 0 → 7.
- **Case B — replay**: the same action attempted a second time through the consumer; correctly rejected, counter unchanged.
- **Case G — hash binding**: `is_executable` with a wrong action hash or wrong policy hash both correctly return `false`.
- **Case C — high/critical friction**: a value-10000 action reached `CRITICAL` (weighted score 400, real semantic contribution plus the deterministic value floor) requiring 2 approvals and an 8s delay. A non-approver's approval attempt was correctly rejected. One approval left it still non-executable. Two real approvals (owner, bob) plus the elapsed delay made it executable; execution advanced the counter 7 → 10.
- **Case D — pause**: a separately assessed, executable action became non-executable the moment its policy was paused, and the policy was reactivated afterward for the next case.
- **Case F — revocation**: a separately assessed, executable action was revoked by the policy owner, immediately became permanently non-executable, and stayed non-executable even after that policy was paused and reactivated again — proving revocation is independent of policy-level state.
- **Case E — retryable non-decision**: not reproducible on demand against the live network (no mock hook exists there); exercised instead in Direct Mode, which supports deterministic injection of a malformed model response and of a raised model-call exception. This is simulated evidence, clearly distinguished from the live cases above.

Final on-chain state: executor counter `10`; Policy 1 and 2 both `SEALED`/`active`; action 1 `ASSESSED` (executed, replay-blocked); action 2 `ASSESSED` (executed); action 3 `ASSESSED` (used for the pause demo); action 4 `REVOKED` (permanent).

## Local verification (all passing on the final source)

- `python -m unittest discover -s tests/unit` — 6/6 pass
- `pytest -q tests/direct` (genlayer-test v0.29.2) — 31/31 pass
- `python scripts/preflight.py` — PASS
- `python scripts/preflight.py --final` — PASS
- `python scripts/check_cli.py` — `OK: genlayer CLI 0.39.1`
- `python scripts/verify_studionet.py` — `OK: Studionet chain ID 61999 at https://studio.genlayer.com/api`

## Scope

No frontend. This is a standalone GenLayer Intelligent Contract primitive (`contracts/riskclock.py`) plus one minimal consumer (`contracts/riskclock_executor.py`) that proves composability.

---

## Archived: earlier session history (superseded, kept for context only)

<details>
<summary>Original generated-package status (before any live deployment)</summary>

Completed in generated package: standalone RiskClock contract, minimal RiskClockExecutor, immutable draft/seal policy lifecycle, four semantic risk dimensions plus deterministic value-at-risk band, a validator that independently reassesses and rejects tier disagreement, malformed-output handling (later redesigned into explicit non-decisions, see above), deterministic weighted scoring/tier mapping/delay/approval requirements, approver allowlist/duplicate protection, policy pause, exact hash binding, consumer replay protection, Direct Mode tests authored (not yet run), pure-Python reference tests authored and executed, network/CLI/RPC lock and verifiers, deployment and live-test documentation, no frontend.

Locally verified at that time: Python syntax compilation, deterministic unit tests, repository preflight. Direct Mode installation could not complete in that build container (no network access to GitHub). Not yet claimed: Direct Mode execution, live deployment, finalized addresses, live consensus lifecycle, explorer evidence, `preflight.py --final`.

</details>

<details>
<summary>First live Studionet session (blocked on a validator interface bug, since fixed)</summary>

Deployed RiskClock at `0x9374d4BEC24A58a1f3b639c21C5Dd79f68B2C1Cd` and RiskClockExecutor at `0x3E329F774aa86EEEb1096dDbFEA6919464E511E9`. Sealed two policies with real hashes and submitted one action. `assess_action` was called 8 times across three script runs and every call finalized with `MAJORITY_DISAGREE`. At the time this was attributed to cross-model heterogeneity among Studionet validator nodes (one receipt showed a leader running `policy:prd-mistral` versus `policy:prd-glm` elsewhere). **This explanation has since been disproven**: the real cause was the `gl.vm.Return` validator bug described above, which caused every leader proposal to be rejected regardless of correctness or which model produced it. Nothing beyond policy sealing and one unassessed action submission was completed in that session. The 8 disagreement transaction hashes from that session are preserved in `deployments/studionet.json` under `historical_pre_fix_deployment` for the record.

</details>
