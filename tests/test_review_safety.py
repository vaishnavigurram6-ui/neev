"""Adversarial arithmetic/evidence checks, using the offline Google stubs."""
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from tests import test_offline  # installs refusing Google clients before imports
from neev_pipeline.tools.boq_analyst_tool import _price, check_rate_deviations
from neev_pipeline.tools.disbursal_risk_tool import assess_tranche
from neev_pipeline.tools.visual_inspector_tool import _finalise, _mime_for, verify_construction_stage


class ReviewSafety(unittest.TestCase):
    def test_no_photos_never_calls_the_model(self):
        with patch("neev_pipeline.tools.visual_inspector_tool._client") as client:
            result = verify_construction_stage([], "slab")
        client.assert_not_called()
        self.assertEqual(result["stage"], "not_assessed")
        self.assertTrue(result["needs_human_review"])
        self.assertFalse(result["matches_claim"])

    def test_extensionless_image_mime_detection(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "artifact"
            for header, mime in ((b"\x89PNG\r\n\x1a\n", "image/png"),
                                 (b"RIFF0000WEBP", "image/webp"),
                                 (b"\xff\xd8\xff", "image/jpeg")):
                path.write_bytes(header)
                self.assertEqual(_mime_for(str(path)), mime)

    def assess(self, **overrides):
        inputs = dict(expected_total_cost=2_000_000, observed_stage="slab",
                      stage_confidence="high", sanctioned_amount=2_000_000,
                      disbursed_cumulative=500_000, completed_value_estimate=3_000_000,
                      matches_claim=True, needs_human_review=False, requested_amount=100_000)
        return assess_tranche(**(inputs | overrides))

    def test_missing_observation_does_not_confirm_claim(self):
        result = _finalise({"confidence": "high", "matches_claim": True}, "slab")
        self.assertEqual(result["stage"], "not_assessed")
        self.assertTrue(result["needs_human_review"])
        self.assertFalse(result["matches_claim"])

    def test_review_gate_and_invalid_confidence_fail_closed(self):
        for fields in ({"needs_human_review": True}, {"stage_confidence": "unknown"}):
            self.assertEqual(self.assess(**fields)["recommendation"], "ESCALATE")

    def test_post_release_exposure_is_checked(self):
        result = self.assess(requested_amount=600_000)
        self.assertEqual(result["recommendation"], "HOLD")
        self.assertEqual(result["projected_exposure_ratio"], 1.1)

    def test_invalid_money_is_rejected(self):
        for value in (-1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                self.assess(disbursed_cumulative=value)

    def test_tonnes_and_kilograms_are_converted(self):
        item = {"desc": "steel", "qty": 1, "unit": "MT", "rate": 60_000,
                "amount": 60_000}
        result = _price([item], [], 1800, {"steel": {"unit": "kg", "benchmark_rate": 60}})
        self.assertEqual(result["fair_price_for_quoted_scope"], 60_000)
        deviation = check_rate_deviations([dict(item="steel", boq_rate=60_000,
                                               unit="MT", benchmark_unit="kg", benchmark_rate=60)])
        self.assertFalse(deviation["steel"]["flag"])
        self.assertEqual(deviation["steel"]["deviation_pct"], 0)

    def test_incompatible_or_missing_units_are_not_compared(self):
        for unit in ("sqm", ""):
            result = check_rate_deviations([dict(item="steel", boq_rate=60_000,
                                                 unit=unit, benchmark_unit="kg", benchmark_rate=60)])
            self.assertFalse(result["steel"]["assessable"])
            self.assertNotIn("deviation_pct", result["steel"])

    def test_unpriced_items_include_missing_benchmarks(self):
        result = _price([{"id": "A", "desc": "unmatched", "qty": 1,
                          "unit": "each", "amount": 300}], [], 1800, {})
        self.assertEqual(result["unpriced_items"], ["A"])
        self.assertEqual(result["fair_price_for_quoted_scope"], 300)

    def test_missing_scope_converted_rate_keeps_area_unit(self):
        result = _price([], ["waterproofing"], 1800,
                        {"waterproofing": {"unit": "sqft", "benchmark_rate": 10}})
        scope = result["missing_scope"][0]
        self.assertEqual(scope["unit"], "sqm")
        self.assertAlmostEqual(scope["rate"], 107.639, places=2)


if __name__ == "__main__":
    unittest.main()