# Deployment lock

RiskClock is built for **stable Studionet only**:

- network: `studionet`
- chain ID: `61999`
- RPC: `https://studio.genlayer.com/api`
- GenLayer CLI: `0.39.1`

## Current live deployment

See `deployments/studionet.json` for the current, factual deployment record (addresses, source hashes, commit SHA, transaction hashes). `BUILD_STATUS.md` carries the same information in prose. Do not treat any address in this file or in git history older than the commit referenced in `deployments/studionet.json` as current.

## Core

```bash
python scripts/preflight.py
python scripts/check_cli.py
python scripts/verify_studionet.py
genlayer deploy --contract contracts/riskclock.py --rpc https://studio.genlayer.com/api
```

## Consumer

After the RiskClock address is final, deploy `contracts/riskclock_executor.py` with constructor values:

1. `riskclock_address`: the finalized RiskClock contract address
2. `target_ref`: `riskclock-demo-counter`

```bash
genlayer deploy --contract contracts/riskclock_executor.py --rpc https://studio.genlayer.com/api \
  --args <riskclock_address> riskclock-demo-counter
```

Use the syntax supported by CLI 0.39.1. Do not upgrade the CLI just to deploy the consumer.

## Redeploying after a contract change

Any change to `contracts/riskclock.py` or `contracts/riskclock_executor.py` invalidates the previous deployment as evidence for the new source. Deploy fresh addresses, verify `genlayer schema <address>` matches the new source's method signatures, and re-run the lifecycle in `docs/LIVE_TEST_PLAN.md` before updating `deployments/studionet.json`. Never present an old address as evidence for changed source.

## After deployment

Run the lifecycle in `docs/LIVE_TEST_PLAN.md` and record real evidence in `deployments/studionet.json`, then `python scripts/preflight.py --final`.
