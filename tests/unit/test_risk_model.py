import json
import unittest

from reference.risk_model import assess, canonical_config, increment_payload_hash, value_level


CONFIG = {
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
    "approvals": {"low": 0, "medium": 1, "high": 2, "critical": 2},
}


class RiskModelTests(unittest.TestCase):
    def test_config_is_canonical(self):
        text = canonical_config(CONFIG)
        self.assertEqual(text, json.dumps(CONFIG, sort_keys=True, separators=(",", ":")))

    def test_low_risk_is_immediate(self):
        result = assess(
            {"reversibility": 0, "privilege_expansion": 0, "external_effect": 0, "recovery_difficulty": 0},
            0,
            CONFIG,
        )
        self.assertEqual(result["tier"], "low")
        self.assertEqual(result["delay_seconds"], 0)
        self.assertEqual(result["approvals_required"], 0)

    def test_value_is_deterministic(self):
        self.assertEqual(value_level(99, CONFIG), 0)
        self.assertEqual(value_level(100, CONFIG), 1)
        self.assertEqual(value_level(1000, CONFIG), 2)
        self.assertEqual(value_level(10000, CONFIG), 3)

    def test_semantic_dimensions_can_force_critical(self):
        result = assess(
            {"reversibility": 3, "privilege_expansion": 3, "external_effect": 3, "recovery_difficulty": 3},
            10000,
            CONFIG,
        )
        self.assertEqual(result["tier"], "critical")
        self.assertEqual(result["delay_seconds"], 86400)
        self.assertEqual(result["approvals_required"], 2)

    def test_payload_hash_is_stable_and_amount_bound(self):
        self.assertEqual(increment_payload_hash(7), increment_payload_hash(7))
        self.assertNotEqual(increment_payload_hash(7), increment_payload_hash(8))

    def test_bad_threshold_order_rejected(self):
        broken = json.loads(json.dumps(CONFIG))
        broken["score_thresholds"] = {"medium": 500, "high": 400, "critical": 900}
        with self.assertRaises(ValueError):
            canonical_config(broken)


if __name__ == "__main__":
    unittest.main()
