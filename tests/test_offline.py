# tests/test_offline.py — offline validation of every non-LLM, non-BigQuery path.
# Runs anywhere (no GCP creds, no network): Google libraries are stubbed so the
# modules import, then the pure math is exercised against the golden Ravi case
# from HANDOFF.md, the clean case, and the low-confidence escalation case.
#
# Run from repo root:  python3 -m tests.test_offline    (or: pytest tests/)

import csv
import os
import re
import sys
import types
import unittest


# ---------------------------------------------------------------- stubs
def _install_stubs():
    """Stub google.cloud.bigquery / google.genai / google.adk so the
    neev_pipeline package imports without the real dependencies or any creds.
    The stubbed clients raise if actually used — these tests only touch
    pure-python code paths."""

    def _module(name):
        mod = sys.modules.get(name)
        if mod is None:
            mod = types.ModuleType(name)
            sys.modules[name] = mod
        return mod

    google = _module("google")
    cloud = _module("google.cloud")
    google.cloud = cloud

    bigquery = _module("google.cloud.bigquery")
    cloud.bigquery = bigquery

    class _NoNetwork:
        def __init__(self, *a, **k):
            raise RuntimeError("BigQuery/Gemini must not be called in offline tests")

    bigquery.Client = _NoNetwork
    bigquery.QueryJobConfig = lambda **k: None
    bigquery.ScalarQueryParameter = lambda *a: None

    genai = _module("google.genai")
    google.genai = genai

    class _StubGenaiClient:  # constructed at visual_inspector_tool import time
        def __init__(self, *a, **k):
            pass

        def __getattr__(self, name):
            raise RuntimeError("Gemini must not be called in offline tests")

    genai.Client = _StubGenaiClient

    adk = _module("google.adk")
    adk_agents = _module("google.adk.agents")
    adk.agents = adk_agents

    class _StubAgent:  # records wiring so the import test can assert on it
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    adk_agents.Agent = _StubAgent
    adk_agents.SequentialAgent = _StubAgent


_install_stubs()

from neev_pipeline import config  # noqa: E402
from neev_pipeline.tools.disbursal_risk_tool import assess_tranche  # noqa: E402
from neev_pipeline.tools.boq_analyst_tool import (  # noqa: E402
    check_rate_deviation,
    check_steel_rcc_ratio,
    check_missing_scope,
    check_payment_schedule,
)


class TestConfig(unittest.TestCase):
    def test_milestone_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(config.MILESTONE_WEIGHTS.values()), 1.0)

    def test_cumulative_weight_monotonic(self):
        weights = [config.cumulative_weight(s) for s in config.MILESTONE_ORDER]
        self.assertEqual(weights, sorted(weights))
        self.assertAlmostEqual(weights[-1], 1.0)

    def test_cumulative_weight_slab(self):
        # foundation 0.15 + plinth 0.10 + slab 0.25
        self.assertAlmostEqual(config.cumulative_weight("slab"), 0.50)

    def test_cumulative_weight_unknown_stage_raises(self):
        with self.assertRaises(ValueError):
            config.cumulative_weight("penthouse")

    def test_ltv_prior_bands(self):
        self.assertEqual(config.ltv_default_prior(50), 0.139)
        self.assertEqual(config.ltv_default_prior(70), 0.126)
        self.assertEqual(config.ltv_default_prior(80), 0.157)
        self.assertEqual(config.ltv_default_prior(90), 0.187)
        self.assertEqual(config.ltv_default_prior(120), 0.267)


class TestDisbursalRisk(unittest.TestCase):
    def test_golden_ravi_case_holds(self):
        # HANDOFF.md golden numbers: expected cost ₹35L, slab stage (50% weight),
        # ₹18L disbursed of ₹28L sanctioned -> exposure 1.03, gap -₹7.5L, HOLD.
        r = assess_tranche(
            expected_total_cost=3_500_000,
            observed_stage="slab",
            stage_confidence="high",
            sanctioned_amount=2_800_000,
            disbursed_cumulative=1_800_000,
            completed_value_estimate=5_400_000,
        )
        self.assertEqual(r["recommendation"], "HOLD")
        self.assertEqual(r["exposure_ratio"], 1.03)
        self.assertEqual(r["cost_to_complete_gap"], -750_000)
        self.assertEqual(r["pct_complete"], 0.50)
        self.assertEqual(r["live_ltv_pct"], 33.3)

    def test_clean_case_releases(self):
        r = assess_tranche(
            expected_total_cost=3_000_000,
            observed_stage="slab",
            stage_confidence="high",
            sanctioned_amount=2_800_000,
            disbursed_cumulative=1_200_000,
            completed_value_estimate=5_400_000,
        )
        self.assertEqual(r["recommendation"], "RELEASE")
        self.assertLessEqual(r["exposure_ratio"], config.EXPOSURE_HOLD_THRESHOLD)
        self.assertGreaterEqual(r["cost_to_complete_gap"], 0)

    def test_low_confidence_escalates_regardless_of_exposure(self):
        r = assess_tranche(
            expected_total_cost=3_000_000,
            observed_stage="slab",
            stage_confidence="low",
            sanctioned_amount=2_800_000,
            disbursed_cumulative=100_000,  # tiny exposure — must still escalate
            completed_value_estimate=5_400_000,
        )
        self.assertEqual(r["recommendation"], "ESCALATE")

    def test_zero_verified_value_is_infinite_exposure_not_crash(self):
        r = assess_tranche(
            expected_total_cost=0,
            observed_stage="slab",
            stage_confidence="high",
            sanctioned_amount=2_800_000,
            disbursed_cumulative=1_000_000,
            completed_value_estimate=0,
        )
        self.assertEqual(r["recommendation"], "HOLD")
        self.assertEqual(r["live_ltv_pct"], 0.0)


class TestBoqChecks(unittest.TestCase):
    def test_rate_deviation_flags_seeded_rcc_flaw(self):
        # Seeded flaw F1: RCC @ ₹9,800 vs ₹8,036 benchmark -> ~22% deviation.
        r = check_rate_deviation(boq_rate=9_800, benchmark_rate=8_036)
        self.assertTrue(r["flag"])
        self.assertAlmostEqual(r["deviation_pct"], 22.0, delta=0.1)

    def test_rate_deviation_within_threshold_not_flagged(self):
        r = check_rate_deviation(boq_rate=8_500, benchmark_rate=8_036)
        self.assertFalse(r["flag"])

    def test_underpricing_also_flagged(self):
        # A too-good-to-be-true rate is a flag too (quality/substitution risk).
        r = check_rate_deviation(boq_rate=6_000, benchmark_rate=8_036)
        self.assertTrue(r["flag"])

    def test_steel_rcc_ratio_flags_padding(self):
        self.assertTrue(check_steel_rcc_ratio(3_000, 50)["flag"])      # 60 kg/cum: thin
        self.assertTrue(check_steel_rcc_ratio(7_000, 50)["flag"])      # 140 kg/cum: padded
        self.assertFalse(check_steel_rcc_ratio(5_000, 50)["flag"])     # 100 kg/cum: sane
        self.assertFalse(check_steel_rcc_ratio(5_000, 0)["flag"] is None)  # no crash on 0

    def test_missing_scope_finds_seeded_waterproofing_gap(self):
        descs = ["RCC M25 for columns", "Electrical conduits and wiring",
                 "CPVC plumbing lines", "Anti-termite treatment",
                 "External plaster 20mm"]
        r = check_missing_scope(descs)
        self.assertEqual(r["missing"], ["waterproofing"])

    def test_missing_scope_clean_boq(self):
        descs = ["waterproofing for terrace", "electrical wiring", "plumbing",
                 "anti-termite treatment", "external plaster"]
        self.assertEqual(check_missing_scope(descs)["missing"], [])

    def test_payment_schedule_flags_seeded_front_loading(self):
        self.assertTrue(check_payment_schedule(0.45)["flag"])   # seeded flaw F4
        self.assertFalse(check_payment_schedule(0.25)["flag"])


class TestBatchedBenchmarkLookup(unittest.TestCase):
    """One query for all 39 items instead of 39 queries.

    The unbatched form made the analyst agent take 81 sequential model turns --
    about two minutes of wall clock and 85% of the run's cost -- because every
    tool call is its own round trip. The row-shaping half is pure, so it is
    tested here without touching BigQuery.
    """

    def _row(self, desc_text, description, unit, rate):
        return types.SimpleNamespace(
            desc_text=desc_text, description=description, unit=unit, effective_rate=rate
        )

    def test_a_matched_item_carries_its_benchmark(self):
        from neev_pipeline.tools.boq_analyst_tool import _shape_benchmark_rows

        rows = [self._row("RCC M25 for slab", "RCC M25 slab", "cum", 8036.0)]
        out = _shape_benchmark_rows(["RCC M25 for slab"], rows)
        self.assertEqual(out["RCC M25 for slab"]["benchmark_rate"], 8036.0)
        self.assertEqual(out["RCC M25 for slab"]["matched_item"], "RCC M25 slab")

    def test_every_input_description_appears_in_the_output(self):
        """A silently dropped item is an unchecked rate, so the shape must be total."""
        from neev_pipeline.tools.boq_analyst_tool import _shape_benchmark_rows

        descs = ["RCC M25 for slab", "MS main gate", "Sand filling"]
        rows = [self._row("RCC M25 for slab", "RCC M25 slab", "cum", 8036.0)]
        out = _shape_benchmark_rows(descs, rows)
        self.assertEqual(sorted(out), sorted(descs))

    def test_an_unmatched_item_says_so_rather_than_guessing(self):
        from neev_pipeline.tools.boq_analyst_tool import _shape_benchmark_rows

        out = _shape_benchmark_rows(["MS main gate"], [])
        self.assertIsNone(out["MS main gate"]["matched_item"])
        self.assertIn("UNBENCHMARKED", out["MS main gate"]["note"])

    def test_a_left_join_miss_row_is_not_mistaken_for_a_match(self):
        """The batched SQL LEFT JOINs, so a miss arrives as a row of NULLs."""
        from neev_pipeline.tools.boq_analyst_tool import _shape_benchmark_rows

        rows = [self._row("MS main gate", None, None, None)]
        out = _shape_benchmark_rows(["MS main gate"], rows)
        self.assertIsNone(out["MS main gate"]["matched_item"])

    def test_a_repeated_description_is_queried_once_and_answered_once(self):
        from neev_pipeline.tools.boq_analyst_tool import _shape_benchmark_rows

        rows = [self._row("Sand filling", "Sand filling under floors", "cum", 1350.0)]
        out = _shape_benchmark_rows(["Sand filling", "Sand filling"], rows)
        self.assertEqual(len(out), 1)
        self.assertEqual(out["Sand filling"]["benchmark_rate"], 1350.0)


class TestBatchedDeviationCheck(unittest.TestCase):
    """The second half of the fan-out.

    Batching only the benchmark lookup left check_rate_deviation being called
    once per matched item -- 28 more model turns. The singular function stays as
    the pure, tested implementation; the plural one is what the agent calls.
    """

    def test_one_call_scores_every_quote(self):
        from neev_pipeline.tools.boq_analyst_tool import check_rate_deviations

        out = check_rate_deviations([
            {"item": "3.1", "boq_rate": 9800, "benchmark_rate": 8036},
            {"item": "1.1", "boq_rate": 285, "benchmark_rate": 252},
        ])
        self.assertTrue(out["3.1"]["flag"])
        self.assertEqual(sorted(out), ["1.1", "3.1"])

    def test_a_quote_missing_its_benchmark_is_reported_not_scored(self):
        """Guards against dividing by a null benchmark for an UNBENCHMARKED item."""
        from neev_pipeline.tools.boq_analyst_tool import check_rate_deviations

        out = check_rate_deviations([{"item": "12.2", "boq_rate": 18000}])
        self.assertFalse(out["12.2"]["flag"])
        self.assertIn("UNBENCHMARKED", out["12.2"]["note"])


class TestPipelineWiring(unittest.TestCase):
    def test_agent_module_imports_and_wires_five_agents(self):
        from neev_pipeline import agent
        names = [a.name for a in agent.root_agent.sub_agents]
        self.assertEqual(names, [
            "boq_analyst_agent", "cost_estimation_agent",
            "visual_inspector_agent", "disbursal_risk_agent",
            "explainer_agent",
        ])

    def test_every_agent_has_output_key(self):
        from neev_pipeline import agent
        for a in agent.root_agent.sub_agents:
            self.assertTrue(getattr(a, "output_key", None), f"{a.name} missing output_key")


class TestPortfolioView(unittest.TestCase):
    """The SQL view hardcodes cumulative milestone weights (BigQuery views
    can't import config.py) — these tests keep SQL and Python in lockstep,
    and sanity-check the screen math against the fixture data."""

    SQL_PATH = os.path.join(os.path.dirname(__file__), "..", "scripts",
                            "portfolio_view.sql")
    CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "fixtures",
                            "draw_schedule.csv")

    def test_sql_weights_match_config(self):
        with open(self.SQL_PATH) as f:
            sql = f.read()
        pairs = re.findall(r"WHEN '(\w+)'\s+THEN ([0-9.]+)", sql)
        self.assertEqual(len(pairs), len(config.MILESTONE_ORDER))
        for stage, weight in pairs:
            self.assertAlmostEqual(
                float(weight), config.cumulative_weight(stage),
                msg=f"SQL weight for '{stage}' drifted from config.py")

    def _screen_fixture(self):
        """Replicate the view's math over draw_schedule.csv."""
        latest = {}
        with open(self.CSV_PATH) as f:
            for row in csv.DictReader(f):
                lid, tno = int(row["loan_id"]), int(row["tranche_no"])
                if lid not in latest or tno > latest[lid]["tranche_no"]:
                    latest[lid] = {
                        "tranche_no": tno,
                        "sanctioned": float(row["sanctioned"]),
                        "disbursed_cum": float(row["disbursed_cum"]),
                        "stage": row["observed_stage"],
                    }
        out = {}
        for lid, r in latest.items():
            pct = config.cumulative_weight(r["stage"])
            exposure = r["disbursed_cum"] / (r["sanctioned"] * pct)
            gap = (r["sanctioned"] - r["disbursed_cum"]) - r["sanctioned"] * (1 - pct)
            out[lid] = {"exposure": round(exposure, 2), "gap": round(gap),
                        "status": "REVIEW" if exposure > 1.0 else "OK"}
        return out

    def test_golden_loan_1001_surfaces_for_review(self):
        screen = self._screen_fixture()
        self.assertIn(1001, screen)
        # ₹18L disbursed at slab (50%) on ₹28L sanctioned → exposure 1.29,
        # gap −₹4L on the sanction-proxy screen → must surface as REVIEW.
        self.assertEqual(screen[1001]["status"], "REVIEW")
        self.assertEqual(screen[1001]["exposure"], 1.29)
        self.assertLess(screen[1001]["gap"], 0)

    def test_screen_is_not_flag_happy(self):
        screen = self._screen_fixture()
        ok = [lid for lid, s in screen.items() if s["status"] == "OK"]
        self.assertGreater(len(ok), 0,
                           "every loan flagged — screen would be useless")

    def test_all_fixture_stages_are_known(self):
        # An unknown stage in the CSV would NULL out in the SQL CASE.
        with open(self.CSV_PATH) as f:
            for row in csv.DictReader(f):
                self.assertIn(row["observed_stage"], config.MILESTONE_ORDER)


class TestFixtureBoQs(unittest.TestCase):
    """Cross-validates BOTH BoQ variants (scripts/boq_data.py) against
    fixtures/rate_benchmarks.csv, replicating the BigQuery lookup's
    longest-keyword matching. Guarantees:
      - the Ravi BoQ triggers EXACTLY the seeded flaws (no accidental extras
        polluting the '4 flags' demo story)
      - the clean BoQ triggers none (the negative test can actually pass)"""

    BENCH_PATH = os.path.join(os.path.dirname(__file__), "..", "fixtures",
                              "rate_benchmarks.csv")

    @classmethod
    def setUpClass(cls):
        from scripts.boq_data import (RAVI_ITEMS, RAVI_PAYMENT, RAVI_META,
                                      CLEAN_ITEMS, CLEAN_PAYMENT, CLEAN_META)
        cls.ravi = (RAVI_ITEMS, RAVI_PAYMENT, RAVI_META)
        cls.clean = (CLEAN_ITEMS, CLEAN_PAYMENT, CLEAN_META)
        with open(cls.BENCH_PATH) as f:
            cls.benchmarks = list(csv.DictReader(f))

    def _lookup(self, desc):
        """Longest-keyword match — same semantics as the BigQuery query."""
        hits = [b for b in self.benchmarks if b["keyword"] in desc.lower()]
        if not hits:
            return None
        return max(hits, key=lambda b: len(b["keyword"]))

    def _rate_flags(self, items):
        flagged = []
        for _, iid, desc, _, _, rate in items:
            b = self._lookup(desc)
            if b is None or rate == 0:
                continue
            r = check_rate_deviation(rate, float(b["effective_rate"]))
            if r["flag"]:
                flagged.append(iid)
        return flagged

    def _pct_before_slab(self, payment):
        pct = 0
        for stage, p in payment:
            if "slab" in stage.lower():
                break
            pct += int(p.rstrip("%"))
        return pct / 100

    def _steel_ratio_ok(self, items):
        steel = sum(q for _, _, d, q, u, _ in items if "tmt" in d.lower() and u == "kg")
        rcc = sum(q for _, _, d, q, u, _ in items if "rcc" in d.lower() and u == "cum")
        return not check_steel_rcc_ratio(steel, rcc)["flag"]

    # ---------------------------------------------------------------- Ravi
    def test_ravi_rate_flags_are_exactly_the_seeded_ones(self):
        items, _, _ = self.ravi
        self.assertEqual(sorted(self._rate_flags(items)), ["2.3", "3.1", "3.2"])

    def test_ravi_missing_scope_is_the_seeded_gap(self):
        items, _, _ = self.ravi
        r = check_missing_scope([d for _, _, d, _, _, _ in items])
        # F2: three absences, one flaw type (MISSING_SCOPE) — and crucially NOT
        # electrical/plumbing, which are present as "wiring"/"CPVC" items.
        self.assertEqual(sorted(r["missing"]),
                         ["anti-termite", "external plaster", "waterproofing"])

    def test_ravi_tmt_is_ungraded_and_payment_front_loaded(self):
        items, payment, meta = self.ravi
        tmt = next(d for _, _, d, _, u, _ in items if "tmt" in d.lower())
        self.assertNotIn("fe500", tmt.lower())            # F3 seeded
        self.assertTrue(check_payment_schedule(self._pct_before_slab(payment))["flag"])
        self.assertNotIn("gst", meta["terms"].lower())    # GST_SILENT seeded
        self.assertTrue(self._steel_ratio_ok(items))      # ratio is NOT a seeded flaw

    # --------------------------------------------------------------- clean
    def test_clean_boq_has_zero_rate_flags(self):
        items, _, _ = self.clean
        self.assertEqual(self._rate_flags(items), [])

    def test_clean_boq_has_full_scope_and_sane_schedule(self):
        items, payment, meta = self.clean
        r = check_missing_scope([d for _, _, d, _, _, _ in items])
        self.assertEqual(r["missing"], [])
        self.assertFalse(check_payment_schedule(self._pct_before_slab(payment))["flag"])
        self.assertIn("gst", meta["terms"].lower())
        self.assertTrue(self._steel_ratio_ok(items))
        tmt = next(d for _, _, d, _, u, _ in items if "tmt" in d.lower())
        self.assertIn("fe500", tmt.lower())
        self.assertIn("is 1786", tmt.lower())

    def test_payment_schedules_sum_to_100(self):
        for _, payment, meta in (self.ravi, self.clean):
            total = sum(int(p.rstrip("%")) for _, p in payment)
            self.assertEqual(total, 100, f"{meta['firm']} schedule sums to {total}%")


if __name__ == "__main__":
    unittest.main(verbosity=2)
