# Agent handoff for Lola

Finish RiskClock completely from the repository folder I have opened for you.

Do not just review it, give me a plan, or return a checklist. Inspect the existing repository, run the actual checks, fix anything necessary, deploy it, collect real live evidence, and push the finished repository to:

`https://github.com/lolaaa00/Riskclock`

## Non-negotiable network lock

RiskClock is for:

- network: **studionet**
- chain ID: **61999**
- RPC: **https://studio.genlayer.com/api**
- GenLayer CLI: **0.39.1**

Do **not** use chain 61997.
Do **not** use Studionet-dev / Studio Next.
Do **not** use Bradbury.
Do **not** install or upgrade to CLI 0.40.0.
If a local CLI is needed, use exactly 0.39.1 and make `python scripts/check_cli.py` pass before any deployment.

## Product scope

RiskClock is a standalone GenLayer Intelligent Contract submission.

It must **not have a frontend**.
Do not add Next.js, React, Vite, wallet UI, dashboard, landing page, or product frontend.

The submission is the primitive itself plus the included tiny consumer contract that proves another IC can enforce the RiskClock gate.

## Read first

Read these files in full before changing anything:

- `README.md`
- `SUBMISSION.md`
- `BUILD_STATUS.md`
- `NETWORK_LOCK.json`
- `docs/ARCHITECTURE.md`
- `docs/SECURITY_MODEL.md`
- `docs/LIVE_TEST_PLAN.md`
- `docs/DEPLOYMENT.md`
- `contracts/riskclock.py`
- `contracts/riskclock_executor.py`
- `tests/direct/test_riskclock.py`

Preserve the core mechanism: GenLayer consensus classifies bounded semantic risk; deterministic code maps the accepted risk vector to delay and approvals. Do not turn it into a generic policy gate or an “AI decides whether action is safe” contract.

## Required execution sequence

1. Confirm the repository is still frontend-free.
2. Run `python scripts/preflight.py`.
3. Install the pinned Direct Mode dependency in an isolated environment and run `pytest -q tests/direct`.
4. Fix any real compatibility issue without changing the network or CLI lock.
5. Run `python scripts/check_cli.py`; it must report 0.39.1.
6. Run `python scripts/verify_studionet.py`; it must report chain ID 61999.
7. Confirm the deployer account and balance. Never expose a private key in logs or commit it.
8. Deploy `contracts/riskclock.py` to stable Studionet and wait for finalization.
9. Deploy `contracts/riskclock_executor.py` using the finalized RiskClock address and target ref `riskclock-demo-counter`.
10. Run the complete lifecycle in `docs/LIVE_TEST_PLAN.md`, including low-risk execution, high-friction assessment, approver enforcement, replay rejection, and policy pause invalidation.
11. Save only real deployment/lifecycle evidence to `deployments/studionet.json` and update `BUILD_STATUS.md` with addresses, tx hashes, test counts and explorer links.
12. Run `python scripts/preflight.py --final` and do not mark the build final until it passes.
13. Push everything to `lolaaa00/Riskclock` on the main branch, preserving unrelated owner work if any appeared after this ZIP was created.

## Important honesty rule

Do not claim a deployment, test, transaction, finalization, or explorer result that you did not personally execute and verify. If stable Studionet or the funded account blocks completion, stop at that exact point and report the concrete blocker while leaving the repo honest.
