# Submission notes

## Purpose

RiskClock is a reusable GenLayer Intelligent Contract primitive for risk-adaptive execution friction. A frozen action is classified across four semantic risk dimensions by independent GenLayer validators, while numeric value risk is deterministic. Immutable policy weights and thresholds then map the vector to LOW/MEDIUM/HIGH/CRITICAL, and deterministic logic assigns the required delay and approval threshold.

## Why GenLayer

Traditional contracts can enforce a numeric delay or signature threshold, but they cannot robustly determine whether a natural-language action is reversible, expands privilege, creates broad external effects, or is difficult to recover from. RiskClock uses GenLayer only for those judgement-heavy dimensions. The LLM never chooses the final friction and cannot lower numeric value risk.

## Consensus

The leader proposes bounded 0..3 semantic levels. Validators independently reassess the same frozen action and policy. A leader is accepted only when the validator derives the same risk tier and no semantic dimension differs by more than one level. Malformed model output fails to maximum semantic risk.

## Reusability

`is_executable(action_id, expected_action_hash, expected_policy_hash)` is the consumer surface. The included `RiskClockExecutor` demonstrates a second Intelligent Contract that can gate a state transition and reject replay.

## Scope

No frontend. No custody. No arbitrary executor. No claim that RiskClock proves an action is safe. It provides a transparent, immutable mapping from consensus-backed risk classification to deterministic execution friction.

## Required network

Studionet 61999, RPC `https://studio.genlayer.com/api`, GenLayer CLI 0.39.1.
