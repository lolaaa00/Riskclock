"""Direct-mode tests for RiskClock.

These tests are intended for genlayer-test v0.29.2, matching the 61999-era
Studionet contract syntax. They are not claimed as executed in the generated ZIP
because the current build container does not include genlayer-test.
"""
import json

CONTRACT = "contracts/riskclock.py"
ASSESSOR = r"RiskClock semantic risk assessor"
PAYLOAD = "11" * 32


def addr(value):
    """Wrap a direct-mode test address (may already be raw bytes) as an
    Address instance. The gltest direct-mode fixtures construct addresses
    before contract SDK paths are registered on sys.path, so they can fall
    back to plain bytes; contract storage fields typed Address require the
    real Address wrapper, which is only importable once the SDK paths have
    been set up by an earlier direct_deploy call."""
    from genlayer.py.types import Address

    return Address(bytes(value))


def config(*, low_approvals=0):
    return json.dumps(
        {
            "weights": {
                "reversibility": 100,
                "privilege_expansion": 100,
                "value_at_risk": 100,
                "external_effect": 100,
                "recovery_difficulty": 100,
            },
            "score_thresholds": {"medium": 200, "high": 500, "critical": 900},
            "value_thresholds": {"medium": 100, "high": 1000, "critical": 10000},
            "delays": {"low": 0, "medium": 60, "high": 3600, "critical": 86400},
            "approvals": {"low": low_approvals, "medium": 1, "high": 2, "critical": 2},
        }
    )


def assessment(rev=0, priv=0, ext=0, rec=0):
    return json.dumps(
        {
            "reversibility": rev,
            "privilege_expansion": priv,
            "external_effect": ext,
            "recovery_difficulty": rec,
            "reason_code": "TEST",
            "reason": "fixture",
        }
    )


def make_policy(contract, owner, bob, cfg=None):
    policy_id = contract.create_policy(
        "Treasury Risk Policy",
        "Treat authority expansion, irreversible state changes, and broad third-party effects conservatively.",
        cfg or config(),
    )
    contract.add_approver(policy_id, addr(owner))
    contract.add_approver(policy_id, addr(bob))
    policy_hash = contract.seal_policy(policy_id)
    return policy_id, policy_hash


def submit(contract, policy_id, value=0, purpose="Increment demo counter by a bounded amount"):
    return contract.submit_action(
        policy_id,
        "riskclock-demo-counter",
        "INCREMENT_COUNTER",
        value,
        PAYLOAD,
        purpose,
    )


def test_policy_must_be_sealed_before_action(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id = contract.create_policy("P", "Conservative risk charter", config())
    with direct_vm.expect_revert("active and sealed"):
        submit(contract, policy_id)


def test_seal_requires_enough_approvers(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id = contract.create_policy("P", "Conservative risk charter", config())
    contract.add_approver(policy_id, addr(direct_alice))
    with direct_vm.expect_revert("more approvals"):
        contract.seal_policy(policy_id)


def test_low_risk_action_maps_to_low_friction(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, policy_hash = make_policy(contract, direct_alice, direct_bob)
    action_id = submit(contract, policy_id, value=0)
    direct_vm.mock_llm(ASSESSOR, assessment())
    contract.assess_action(action_id)

    action = contract.get_action(action_id)
    assert action["tier_name"] == "LOW"
    assert action["weighted_score"] == 0
    assert action["delay_seconds"] == 0
    assert action["approvals_required"] == 0
    assert contract.is_executable(action_id, action["action_hash"], policy_hash) is True


def test_deterministic_value_floor_contributes_to_tier(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, _ = make_policy(contract, direct_alice, direct_bob)
    action_id = submit(contract, policy_id, value=10000)
    direct_vm.mock_llm(ASSESSOR, assessment())
    contract.assess_action(action_id)
    action = contract.get_action(action_id)
    assert action["risk_vector"]["value_at_risk"] == 3
    assert action["weighted_score"] == 300
    assert action["tier_name"] == "MEDIUM"


def test_semantic_risk_can_force_critical_friction(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, _ = make_policy(contract, direct_alice, direct_bob)
    action_id = submit(contract, policy_id, value=10000)
    direct_vm.mock_llm(ASSESSOR, assessment(3, 3, 3, 3))
    contract.assess_action(action_id)
    action = contract.get_action(action_id)
    assert action["tier_name"] == "CRITICAL"
    assert action["delay_seconds"] == 86400
    assert action["approvals_required"] == 2


def test_malformed_model_output_fails_closed(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, _ = make_policy(contract, direct_alice, direct_bob)
    action_id = submit(contract, policy_id, value=10000)
    direct_vm.mock_llm(ASSESSOR, "not json")
    contract.assess_action(action_id)
    action = contract.get_action(action_id)
    assert action["tier_name"] == "CRITICAL"
    assert "MALFORMED_MODEL_OUTPUT" in action["reason"]


def test_validator_rejects_different_execution_tier(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, _ = make_policy(contract, direct_alice, direct_bob)
    action_id = submit(contract, policy_id, value=0)
    direct_vm.mock_llm(ASSESSOR, assessment(0, 0, 0, 0))
    contract.assess_action(action_id)
    assert contract.get_action(action_id)["tier_name"] == "LOW"

    direct_vm.clear_mocks()
    direct_vm.mock_llm(ASSESSOR, assessment(3, 3, 3, 3))
    assert direct_vm.run_validator() is False


def test_approval_is_whitelisted_and_non_replayable(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, _ = make_policy(contract, direct_alice, direct_bob, config(low_approvals=1))
    action_id = submit(contract, policy_id, value=0)
    direct_vm.mock_llm(ASSESSOR, assessment())
    contract.assess_action(action_id)

    with direct_vm.prank(direct_bob):
        contract.approve_action(action_id)
        with direct_vm.expect_revert("duplicate approval"):
            contract.approve_action(action_id)

    assert contract.get_action(action_id)["approval_count"] == 1


def test_policy_pause_invalidates_gate(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, policy_hash = make_policy(contract, direct_alice, direct_bob)
    action_id = submit(contract, policy_id)
    direct_vm.mock_llm(ASSESSOR, assessment())
    contract.assess_action(action_id)
    action_hash = contract.get_action(action_id)["action_hash"]
    assert contract.is_executable(action_id, action_hash, policy_hash) is True
    contract.set_policy_active(policy_id, False)
    assert contract.is_executable(action_id, action_hash, policy_hash) is False


def test_only_pending_action_can_be_cancelled(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, _ = make_policy(contract, direct_alice, direct_bob)
    action_id = submit(contract, policy_id)
    contract.cancel_action(action_id)
    assert contract.get_action(action_id)["status"] == 2
    with direct_vm.expect_revert("only pending"):
        contract.cancel_action(action_id)
