# Deployment evidence

This folder is intentionally empty of contract addresses in the generated ZIP.
Lola's agent should create `studionet.json` only after real deployments on chain 61999.

Expected shape:

```json
{
  "network": "studionet",
  "chain_id": 61999,
  "rpc": "https://studio.genlayer.com/api",
  "cli_version": "0.39.1",
  "riskclock_address": "0x...",
  "executor_address": "0x...",
  "deployment_transactions": [],
  "lifecycle_transactions": [],
  "notes": "real evidence only"
}
```
