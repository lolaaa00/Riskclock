# Deployment lock

RiskClock is built for **stable Studionet only** in this package:

- network: `studionet`
- chain ID: `61999`
- RPC: `https://studio.genlayer.com/api`
- GenLayer CLI: `0.39.1`

The generated repository intentionally does not contain a deployment address because no owner wallet or funded deployer is available in this environment.

## Core

```bash
python scripts/preflight.py
python scripts/check_cli.py
python scripts/verify_studionet.py
python scripts/deploy_studionet.py
```

## Consumer

After the RiskClock address is final, deploy `contracts/riskclock_executor.py` with constructor values:

1. `riskclock_address`: the finalized RiskClock contract address
2. `target_ref`: `riskclock-demo-counter`

Use the syntax supported by CLI 0.39.1 or the stable Studio deployment form. Do not upgrade the CLI just to deploy the consumer.

After both deployments, execute the lifecycle in `LIVE_TEST_PLAN.md` and save real evidence to `deployments/studionet.json`.
