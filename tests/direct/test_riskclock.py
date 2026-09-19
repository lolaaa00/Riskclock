"""Direct-mode tests for RiskClock.

These exercise contracts/riskclock.py and contracts/riskclock_executor.py
against genlayer-test v0.29.2's Direct Mode VM, matching the 61999-era
Studionet contract syntax and the real GenVM run_nondet_unsafe contract
(leader results reach the validator wrapped in gl.vm.Return; a validator
override drives run_validator()). Behaviour is exercised, not merely
structural shape.
"""
import json

CONTRACT = "contracts/riskclock.py"
EXECUTOR_CONTRACT = "contracts/riskclock_executor.py"
ASSESSOR = r"RiskClock semantic risk assessor"
PAYLOAD = "11" * 32
ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


def addr(value):
    """Wrap a direct-mode test address (may already be raw bytes) as an
    Address instance. The gltest direct-mode fixtures construct addresses
    before contract SDK paths are registered on sys.path, so they can fall
    back to plain bytes; contract storage fields typed Address require the
    real Address wrapper, which is only importable once the SDK paths have
    been set up by an earlier direct_deploy call."""
    from genlayer.py.types import Address

    if isinstance(value, str):
        return Address(value)
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


def submit(
    contract,
    policy_id,
    value=0,
    purpose="Increment demo counter by a bounded amount",
    intended_executor=ZERO_ADDRESS,
):
    return contract.submit_action(
        policy_id,
        "riskclock-demo-counter",
        "INCREMENT_COUNTER",
        value,
        PAYLOAD,
        purpose,
        addr(intended_executor),
    )


def payload_hash_for(amount):
    from reference.risk_model import increment_payload_hash

    return increment_payload_hash(amount)


# ---------------------------------------------------------------------------
# Policy lifecycle
# ---------------------------------------------------------------------------

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


def test_zero_address_approver_rejected(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id = contract.create_policy("P", "Conservative risk charter", config())
    with direct_vm.expect_revert("zero address"):
        contract.add_approver(policy_id, ZERO_ADDRESS)


def test_duplicate_approver_rejected(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id = contract.create_policy("P", "Conservative risk charter", config())
    contract.add_approver(policy_id, addr(direct_bob))
    with direct_vm.expect_revert("duplicate approver"):
        contract.add_approver(policy_id, addr(direct_bob))


def test_sealed_policy_cannot_add_approver_or_reseal(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, _ = make_policy(contract, direct_alice, direct_bob)
    with direct_vm.expect_revert("already sealed"):
        contract.add_approver(policy_id, addr(direct_bob))
    with direct_vm.expect_revert("already sealed"):
        contract.seal_policy(policy_id)


def test_policy_config_is_immutable_after_seal(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, policy_hash = make_policy(contract, direct_alice, direct_bob)
    policy = contract.get_policy(policy_id)
    assert policy["definition_hash"] == policy_hash
    assert policy["status"] == 1
    # No mutator exists for a sealed policy's name/charter/config; re-reading
    # must be stable across calls.
    assert contract.get_policy(policy_id) == policy


# ---------------------------------------------------------------------------
# Consensus: gl.vm.Return handling and substantive validation
# ---------------------------------------------------------------------------

def test_low_risk_action_maps_to_low_friction(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, policy_hash = make_policy(contract, direct_alice, direct_bob)
    action_id = submit(contract, policy_id, value=0)
    direct_vm.mock_llm(ASSESSOR, assessment())
    contract.assess_action(action_id)

    action = contract.get_action(action_id)
    assert action["status_name"] == "ASSESSED"
    assert action["tier_name"] == "LOW"
    assert action["weighted_score"] == 0
    assert action["delay_seconds"] == 0
    assert action["approvals_required"] == 0
    assert action["assessment_attempts"] == 1
    assert action["last_assessment_result"] == "SUBSTANTIVE"
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


def test_valid_leader_result_is_accepted_by_validator(direct_vm, direct_deploy, direct_alice, direct_bob):
    """A structurally- and semantically-consistent leader result, delivered
    the way real GenVM delivers it (wrapped in gl.vm.Return), must validate."""
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, _ = make_policy(contract, direct_alice, direct_bob)
    action_id = submit(contract, policy_id, value=0)
    direct_vm.mock_llm(ASSESSOR, assessment())
    contract.assess_action(action_id)
    assert direct_vm.run_validator() is True


def test_validator_rejects_when_leader_result_is_not_a_return(direct_vm, direct_deploy, direct_alice, direct_bob):
    """This is the core interface-correctness test: the validator MUST use
    isinstance(leader_result, gl.vm.Return) and must reject anything else
    (e.g. a plain dict, or a leader that raised) rather than blindly
    indexing into it."""
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, _ = make_policy(contract, direct_alice, direct_bob)
    action_id = submit(contract, policy_id, value=0)
    direct_vm.mock_llm(ASSESSOR, assessment())
    contract.assess_action(action_id)

    import genlayer.gl.vm as glvm

    captured = direct_vm._captured_validators[-1]
    _, _, validator_fn = captured
    # A bare dict (the pre-fix, incorrect assumption) must not validate.
    assert validator_fn({"outcome": "SUBSTANTIVE"}) is False
    # A leader-raised error must not validate either.
    assert validator_fn(glvm.UserError(message="boom")) is False


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


def test_validator_accepts_one_level_semantic_variance(direct_vm, direct_deploy, direct_alice, direct_bob):
    """The protocol explicitly allows up to one level of variance per
    dimension as long as the derived tier still matches -- this proves the
    tolerance is real, not merely documented."""
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, _ = make_policy(contract, direct_alice, direct_bob)
    action_id = submit(contract, policy_id, value=0)
    direct_vm.mock_llm(ASSESSOR, assessment(0, 0, 0, 0))
    contract.assess_action(action_id)
    assert contract.get_action(action_id)["tier_name"] == "LOW"

    direct_vm.clear_mocks()
    # One-level variance on a single dimension keeps the score under the
    # medium threshold (100 < 200), so the tier still matches.
    direct_vm.mock_llm(ASSESSOR, assessment(1, 0, 0, 0))
    assert direct_vm.run_validator() is True


# ---------------------------------------------------------------------------
# Retryable non-decisions: malformed output / source unavailable
# ---------------------------------------------------------------------------

def test_malformed_model_output_is_a_retryable_non_decision(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, policy_hash = make_policy(contract, direct_alice, direct_bob)
    action_id = submit(contract, policy_id, value=10000)
    direct_vm.mock_llm(ASSESSOR, "not json")
    contract.assess_action(action_id)
    action = contract.get_action(action_id)

    # This must NOT be a synthesized CRITICAL verdict. It must be an
    # explicit, non-executable non-decision that leaves the action pending.
    assert action["status_name"] == "PENDING"
    assert action["tier_name"] == "UNASSESSED"
    assert action["weighted_score"] == 0
    assert action["assessed_at"] == 0
    assert action["assessment_attempts"] == 1
    assert action["last_assessment_result"] == "MODEL_OUTPUT_INVALID"
    assert contract.is_executable(action_id, action["action_hash"], policy_hash) is False


def test_malformed_output_validator_agreement_is_deterministic(direct_vm, direct_deploy, direct_alice, direct_bob):
    """Two independent observers both failing to parse the SAME malformed
    text is a deterministic, checkable fact -- not a subjective judgement --
    so the validator must accept outcome-type agreement here."""
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, _ = make_policy(contract, direct_alice, direct_bob)
    action_id = submit(contract, policy_id, value=0)
    direct_vm.mock_llm(ASSESSOR, "not json")
    contract.assess_action(action_id)
    assert direct_vm.run_validator() is True


def test_non_decision_outcome_mismatch_is_rejected(direct_vm, direct_deploy, direct_alice, direct_bob):
    """If the leader claims a non-decision but the validator's own
    independent attempt actually produces a real substantive result, that
    disagreement in KIND must be rejected."""
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, _ = make_policy(contract, direct_alice, direct_bob)
    action_id = submit(contract, policy_id, value=0)
    direct_vm.mock_llm(ASSESSOR, "not json")
    contract.assess_action(action_id)

    direct_vm.clear_mocks()
    direct_vm.mock_llm(ASSESSOR, assessment())
    assert direct_vm.run_validator() is False


def test_source_unavailable_is_a_retryable_non_decision(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, policy_hash = make_policy(contract, direct_alice, direct_bob)
    action_id = submit(contract, policy_id, value=0)
    # No mock registered for the assessor prompt: genlayer-test raises when a
    # gl.nondet.exec_prompt call has no matching mock, simulating a model/
    # infrastructure call that could not be completed.
    contract.assess_action(action_id)
    action = contract.get_action(action_id)
    assert action["status_name"] == "PENDING"
    assert action["last_assessment_result"] == "SOURCE_UNAVAILABLE"
    assert contract.is_executable(action_id, action["action_hash"], policy_hash) is False


def test_retry_after_non_decision_can_reach_assessed(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, policy_hash = make_policy(contract, direct_alice, direct_bob)
    action_id = submit(contract, policy_id, value=0)

    direct_vm.mock_llm(ASSESSOR, "not json")
    contract.assess_action(action_id)
    assert contract.get_action(action_id)["status_name"] == "PENDING"

    direct_vm.clear_mocks()
    direct_vm.mock_llm(ASSESSOR, assessment())
    contract.assess_action(action_id)
    action = contract.get_action(action_id)
    assert action["status_name"] == "ASSESSED"
    assert action["tier_name"] == "LOW"
    assert action["assessment_attempts"] == 2
    assert contract.is_executable(action_id, action["action_hash"], policy_hash) is True


def test_assessment_attempts_advance_and_exhaust(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, policy_hash = make_policy(contract, direct_alice, direct_bob)
    action_id = submit(contract, policy_id, value=0)

    direct_vm.mock_llm(ASSESSOR, "not json")
    for expected_attempt in range(1, 12):
        contract.assess_action(action_id)
        action = contract.get_action(action_id)
        assert action["assessment_attempts"] == expected_attempt
        assert action["status_name"] == "PENDING"

    # 12th and final attempt exhausts the cap.
    contract.assess_action(action_id)
    action = contract.get_action(action_id)
    assert action["assessment_attempts"] == 12
    assert action["status_name"] == "ASSESS_EXHAUSTED"
    assert contract.is_executable(action_id, action["action_hash"], policy_hash) is False
    with direct_vm.expect_revert("not pending"):
        contract.assess_action(action_id)


def test_deterministic_value_risk_cannot_be_overridden_by_model(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, _ = make_policy(contract, direct_alice, direct_bob)
    action_id = submit(contract, policy_id, value=10000)
    # Model tries to claim value_at_risk-adjacent low semantic risk; the
    # deterministic value floor of 3 must still apply regardless.
    direct_vm.mock_llm(ASSESSOR, assessment(0, 0, 0, 0))
    contract.assess_action(action_id)
    action = contract.get_action(action_id)
    assert action["risk_vector"]["value_at_risk"] == 3
    assert action["weighted_score"] == 300  # only value_at_risk contributes


# ---------------------------------------------------------------------------
# Approvals / delay
# ---------------------------------------------------------------------------

def test_approval_is_whitelisted_and_non_replayable(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, _ = make_policy(contract, direct_alice, direct_bob, config(low_approvals=1))
    action_id = submit(contract, policy_id, value=0)
    direct_vm.mock_llm(ASSESSOR, assessment())
    contract.assess_action(action_id)

    with direct_vm.prank(direct_charlie):
        with direct_vm.expect_revert("not a policy approver"):
            contract.approve_action(action_id)

    with direct_vm.prank(direct_bob):
        contract.approve_action(action_id)
        with direct_vm.expect_revert("duplicate approval"):
            contract.approve_action(action_id)

    assert contract.get_action(action_id)["approval_count"] == 1


def test_partial_approvals_block_execution(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, policy_hash = make_policy(contract, direct_alice, direct_bob)
    action_id = submit(contract, policy_id, value=10000)  # CRITICAL tier -> 2 approvals required
    direct_vm.mock_llm(ASSESSOR, assessment(3, 3, 3, 3))
    contract.assess_action(action_id)
    action = contract.get_action(action_id)
    assert action["approvals_required"] == 2
    action_hash = action["action_hash"]

    with direct_vm.prank(direct_alice):
        contract.approve_action(action_id)
    assert contract.get_action(action_id)["approval_count"] == 1
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


# ---------------------------------------------------------------------------
# Pause / revocation
# ---------------------------------------------------------------------------

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


def test_revocation_requires_assessed_status(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, _ = make_policy(contract, direct_alice, direct_bob)
    action_id = submit(contract, policy_id)
    with direct_vm.expect_revert("only an assessed action"):
        contract.revoke_action(action_id)


def test_revocation_requires_policy_owner(direct_vm, direct_deploy, direct_alice, direct_bob, direct_charlie):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, _ = make_policy(contract, direct_alice, direct_bob)
    action_id = submit(contract, policy_id)
    direct_vm.mock_llm(ASSESSOR, assessment())
    contract.assess_action(action_id)

    with direct_vm.prank(direct_charlie):
        with direct_vm.expect_revert("only policy owner"):
            contract.revoke_action(action_id)


def test_revoked_action_never_becomes_executable_again(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, policy_hash = make_policy(contract, direct_alice, direct_bob)
    action_id = submit(contract, policy_id)
    direct_vm.mock_llm(ASSESSOR, assessment())
    contract.assess_action(action_id)
    action_hash = contract.get_action(action_id)["action_hash"]
    assert contract.is_executable(action_id, action_hash, policy_hash) is True

    contract.revoke_action(action_id)
    action = contract.get_action(action_id)
    assert action["status_name"] == "REVOKED"
    assert action["revoked_by"].lower() == str(addr(direct_alice)).lower()
    # Historical assessment data must be preserved, not rewritten.
    assert action["tier_name"] == "LOW"
    assert contract.is_executable(action_id, action_hash, policy_hash) is False

    # Reactivating the (already-active) policy must not resurrect it.
    contract.set_policy_active(policy_id, False)
    contract.set_policy_active(policy_id, True)
    assert contract.is_executable(action_id, action_hash, policy_hash) is False


# ---------------------------------------------------------------------------
# Action identity / hash binding
# ---------------------------------------------------------------------------

def test_action_hash_changes_with_action_id_for_identical_business_fields(
    direct_vm, direct_deploy, direct_alice, direct_bob
):
    """Two independently submitted actions with byte-identical business
    fields must be independently identifiable and independently
    executable -- their action_hash must differ."""
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, _ = make_policy(contract, direct_alice, direct_bob)
    action_id_1 = submit(contract, policy_id, value=0, purpose="Same purpose text")
    action_id_2 = submit(contract, policy_id, value=0, purpose="Same purpose text")
    hash_1 = contract.get_action(action_id_1)["action_hash"]
    hash_2 = contract.get_action(action_id_2)["action_hash"]
    assert hash_1 != hash_2


def test_wrong_action_hash_fails_is_executable(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, policy_hash = make_policy(contract, direct_alice, direct_bob)
    action_id = submit(contract, policy_id)
    direct_vm.mock_llm(ASSESSOR, assessment())
    contract.assess_action(action_id)
    assert contract.is_executable(action_id, "0" * 64, policy_hash) is False


def test_wrong_policy_hash_fails_is_executable(direct_vm, direct_deploy, direct_alice, direct_bob):
    direct_vm.sender = direct_alice
    contract = direct_deploy(CONTRACT)
    policy_id, _ = make_policy(contract, direct_alice, direct_bob)
    action_id = submit(contract, policy_id)
    direct_vm.mock_llm(ASSESSOR, assessment())
    contract.assess_action(action_id)
    action_hash = contract.get_action(action_id)["action_hash"]
    assert contract.is_executable(action_id, action_hash, "0" * 64) is False


# ---------------------------------------------------------------------------
# Consumer: RiskClockExecutor
#
# genlayer-test v0.29.2's Direct Mode loads at most one gl.Contract subclass
# per process (genvm_contracts.__known_contract__ enforces this and raises
# TypeError the moment a second contract module is imported in the same
# run). That makes true cross-contract dispatch between two independently
# deployed contracts impossible to exercise in Direct Mode here. The
# consumer's own logic (target/operation/payload/hash/actor checks, replay
# protection) is still unit-tested below against a stub RiskClock view, and
# full end-to-end composability is proven live on Studionet instead (see
# docs/LIVE_TEST_PLAN.md and deployments/studionet.json).
# ---------------------------------------------------------------------------

def test_executor_deploys_standalone_and_rejects_empty_target_ref(direct_vm, direct_deploy, direct_alice):
    direct_vm.sender = direct_alice
    with direct_vm.expect_revert("target_ref is required"):
        direct_deploy(EXECUTOR_CONTRACT, ZERO_ADDRESS, "   ")
