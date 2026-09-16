# v0.2.18-compatible Studionet consumer contract
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from genlayer import *

import json
from dataclasses import dataclass


@gl.contract_interface
class IRiskClock:
    class View:
        def get_action(self, action_id: u256) -> dict: ...
        def is_executable(
            self,
            action_id: u256,
            expected_action_hash: str,
            expected_policy_hash: str,
        ) -> bool: ...

    class Write:
        pass


@allow_storage
@dataclass
class ExecutionReceipt:
    caller: Address
    action_id: u256
    action_hash: str
    policy_hash: str
    amount: u256


class RiskClockExecutor(gl.Contract):
    """Minimal consumer proving RiskClock can gate a real state transition.

    The consumer exposes exactly one operation, INCREMENT_COUNTER. The submitted
    RiskClock action must target this executor's immutable target_ref and bind
    the exact amount through payload_hash. Replay is impossible because each
    action hash can execute only once here.
    """

    riskclock_address: Address
    target_ref: str
    counter: u256
    executions: TreeMap[str, ExecutionReceipt]

    def __init__(self, riskclock_address: Address, target_ref: str):
        target_ref = " ".join(str(target_ref).strip().split())[:180]
        if target_ref == "":
            raise gl.vm.UserError("EXPECTED: target_ref is required")
        self.riskclock_address = riskclock_address
        self.target_ref = target_ref
        self.counter = u256(0)

    def _payload_hash(self, amount: int) -> str:
        payload = json.dumps(
            {"amount": int(amount)},
            sort_keys=True,
            separators=(",", ":"),
        )
        return Keccak256(payload.encode("utf-8")).hexdigest()

    @gl.public.write
    def execute_increment(
        self,
        action_id: u256,
        expected_action_hash: str,
        expected_policy_hash: str,
        amount: u256,
    ) -> None:
        riskclock = IRiskClock(self.riskclock_address)
        action = riskclock.view().get_action(action_id)

        if str(action.get("target_ref", "")) != str(self.target_ref):
            raise gl.vm.UserError("EXPECTED: action targets a different consumer")
        if str(action.get("operation", "")).upper() != "INCREMENT_COUNTER":
            raise gl.vm.UserError("EXPECTED: unsupported operation")
        if str(action.get("payload_hash", "")).lower() != self._payload_hash(int(amount)).lower():
            raise gl.vm.UserError("EXPECTED: payload hash does not bind this amount")
        if str(action.get("action_hash", "")).lower() != str(expected_action_hash).strip().lower():
            raise gl.vm.UserError("EXPECTED: action hash mismatch")
        if str(action.get("policy_hash", "")).lower() != str(expected_policy_hash).strip().lower():
            raise gl.vm.UserError("EXPECTED: policy hash mismatch")

        if not riskclock.view().is_executable(
            action_id,
            expected_action_hash,
            expected_policy_hash,
        ):
            raise gl.vm.UserError("EXPECTED: RiskClock gate is not executable")

        key = str(expected_action_hash).strip().lower()
        if key in self.executions:
            raise gl.vm.UserError("EXPECTED: action already executed")

        self.counter = u256(int(self.counter) + int(amount))
        self.executions[key] = ExecutionReceipt(
            caller=gl.message.sender_address,
            action_id=action_id,
            action_hash=key,
            policy_hash=str(expected_policy_hash).strip().lower(),
            amount=amount,
        )

    @gl.public.view
    def get_counter(self) -> u256:
        return self.counter

    @gl.public.view
    def was_executed(self, action_hash: str) -> bool:
        return str(action_hash).strip().lower() in self.executions
