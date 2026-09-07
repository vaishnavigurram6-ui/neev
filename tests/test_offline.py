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

    # visual_inspector_tool builds inline image parts, so the stub has to carry
    # google.genai.types as well. It only ever needs to be constructible here --
    # the stubbed client raises before any part is actually sent.
    genai_types = _module("google.genai.types")

    class _Part:
        @staticmethod
        def from_text(text=""):
            return ("text", text)

        @staticmethod
        def from_bytes(data=b"", mime_type=""):
            return ("bytes", mime_type, len(data))

    class _Content:
        def __init__(self, role="user", parts=None):
            self.role, self.parts = role, parts or []

    genai_types.Part = _Part
    genai_types.Content = _Content
    genai.types = genai_types

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


class TestUnverifiableStage(unittest.TestCase):
    """A tranche review with no usable photo must not crash the pipeline.

    Found by the first real captured run. With no photos supplied,
    visual_inspector_agent correctly reported stage "not_assessed"; assess_tranche
    called cumulative_weight() on it before the confidence gate and raised
    ValueError, taking the whole five-agent run down after several billed calls.

    The honest answer is INSPECT: progress that cannot be verified cannot justify
    a release. The schema already carries exposure_undefined for exactly this.
    """

    def _assess(self, stage, confidence="high"):
        from neev_pipeline.tools.disbursal_risk_tool import assess_tranche

        return assess_tranche(
            expected_total_cost=3_235_794,
            observed_stage=stage,
            stage_confidence=confidence,
            sanctioned_amount=2_800_000,
            disbursed_cumulative=1_800_000,
            completed_value_estimate=8_099_999,
        )

    def test_not_assessed_recommends_inspect_instead_of_raising(self):
        r = self._assess("not_assessed")
        self.assertEqual(r["recommendation"], "INSPECT")

    def test_an_unverifiable_stage_reports_no_exposure_rather_than_a_wrong_one(self):
        r = self._assess("not_assessed")
        self.assertTrue(r["exposure_undefined"])
        self.assertIsNone(r["exposure_ratio"])

    def test_the_reason_says_why_a_decision_could_not_be_made(self):
        r = self._assess("not_assessed")
        self.assertTrue(any("verif" in x.lower() or "photo" in x.lower() for x in r["reasons"]))

    def test_any_unrecognised_stage_is_treated_the_same_way(self):
        self.assertEqual(self._assess("unknown")["recommendation"], "INSPECT")
        self.assertEqual(self._assess("")["recommendation"], "INSPECT")

    def test_a_real_stage_still_decides_normally(self):
        """Guards against the fix swallowing the cases that already worked."""
        self.assertEqual(self._assess("slab")["recommendation"], "HOLD")
        self.assertFalse(self._assess("slab")["exposure_undefined"])


class TestEvidenceContradictingTheClaim(unittest.TestCase):
    """A photo that contradicts the claim must not release money.

    The first captured run of loan 1002 returned matches_claim false with a note
    that the photo showed a G+1 structure against a G+0 plan -- a real finding,
    of exactly the kind this product exists to surface. assess_tranche never
    read matches_claim, so it recommended RELEASE anyway, and 12 lakh would have
    gone out against a building that is not the one financed.
    """

    def _assess(self, **over):
        from neev_pipeline.tools.disbursal_risk_tool import assess_tranche

        kwargs = dict(
            expected_total_cost=2_966_145,
            observed_stage="slab",
            stage_confidence="high",
            sanctioned_amount=2_500_000,
            disbursed_cumulative=1_214_337,
            completed_value_estimate=8_099_999,
        )
        kwargs.update(over)
        return assess_tranche(**kwargs)

    def test_evidence_that_backs_the_claim_still_releases(self):
        r = self._assess(matches_claim=True)
        self.assertEqual(r["recommendation"], "RELEASE")

    def test_evidence_contradicting_the_claim_escalates_instead(self):
        r = self._assess(matches_claim=False)
        self.assertEqual(r["recommendation"], "ESCALATE")

    def test_the_reason_names_the_contradiction(self):
        r = self._assess(matches_claim=False)
        self.assertTrue(any("contradict" in x.lower() or "does not match" in x.lower()
                            for x in r["reasons"]))

    def test_a_contradiction_outranks_a_comfortable_exposure(self):
        """Low exposure must not let a contradicted claim through."""
        r = self._assess(matches_claim=False, disbursed_cumulative=100_000)
        self.assertEqual(r["recommendation"], "ESCALATE")

    def test_omitting_matches_claim_keeps_the_old_behaviour(self):
        self.assertEqual(self._assess()["recommendation"], "RELEASE")


class TestObservedStageIsNotOverwritten(unittest.TestCase):
    """verify_construction_stage set result["stage"] = claimed_stage, always.

    So the "verified" stage downstream was the borrower's claim rather than
    anything observed, and the verification was cosmetic.
    """

    def test_the_reported_stage_is_what_was_seen_not_what_was_claimed(self):
        import neev_pipeline.tools.visual_inspector_tool as vit

        result = vit._finalise({"observed_stage": "plinth", "confidence": "high",
                                "matches_claim": False}, claimed_stage="slab")
        self.assertEqual(result["stage"], "plinth")
        self.assertEqual(result["claimed_stage"], "slab")

    def test_it_falls_back_to_the_claim_only_when_nothing_was_observed(self):
        import neev_pipeline.tools.visual_inspector_tool as vit

        result = vit._finalise({"confidence": "high", "matches_claim": True},
                               claimed_stage="slab")
        self.assertEqual(result["stage"], "slab")

    def test_low_confidence_still_forces_human_review(self):
        import neev_pipeline.tools.visual_inspector_tool as vit

        result = vit._finalise({"confidence": "low"}, claimed_stage="slab")
        self.assertTrue(result["needs_human_review"])


class TestCostToCompleteIsReported(unittest.TestCase):
    """assess_tranche computed remaining_cost and threw it away.

    It was only ever used to derive the gap, so "Needed to finish" on Build
    Progress and "Cost to complete" on Tranche Decision both rendered an em
    dash on a real capture -- while the gap derived from it printed fine.
    """

    def _assess(self, **over):
        from neev_pipeline.tools.disbursal_risk_tool import assess_tranche

        kwargs = dict(
            expected_total_cost=3_235_794,
            observed_stage="slab",
            stage_confidence="high",
            sanctioned_amount=2_800_000,
            disbursed_cumulative=1_800_000,
            completed_value_estimate=8_099_999,
        )
        kwargs.update(over)
        return assess_tranche(**kwargs)

    def test_cost_to_complete_is_the_unbuilt_share_of_the_expected_cost(self):
        r = self._assess()
        self.assertAlmostEqual(r["cost_to_complete"], 3_235_794 * 0.5, delta=1)

    def test_the_gap_still_reconciles_with_it(self):
        """gap = what is left in the sanction, minus what is left to build."""
        r = self._assess()
        left_in_sanction = 2_800_000 - 1_800_000
        self.assertAlmostEqual(
            r["cost_to_complete_gap"], left_in_sanction - r["cost_to_complete"], delta=1
        )

    def test_an_unverifiable_stage_reports_the_whole_build_as_remaining(self):
        r = self._assess(observed_stage="not_assessed")
        self.assertEqual(r["cost_to_complete"], 3_235_794)


class TestPricingAbsentScope(unittest.TestCase):
    """What the missing scope would cost, from benchmarks -- never from a guess.

    The MISSING SCOPE card read 0 next to three missing-scope flags, because
    cost_estimate.missing_scope_value was never populated. Pricing absent work
    needs an area, so it belongs in a tool with documented factors rather than
    in a prompt: this is exactly the "no invented figures" case.
    """

    # Benchmarks as lookup_benchmark_rates returns them, so the arithmetic is
    # exercised without a query. Rates are the real ones from
    # fixtures/rate_benchmarks.csv; anti-termite deliberately has none.
    BENCH = {
        "RCC M25 for slab": {"matched_item": "RCC M25", "unit": "cum",
                             "benchmark_rate": 8036.0},
        "MS main gate": {"matched_item": None},
        "waterproofing": {"matched_item": "Brickbat coba", "unit": "sqm",
                          "benchmark_rate": 620.0},
        "external plaster": {"matched_item": "18mm external plaster",
                             "unit": "sqm", "benchmark_rate": 240.0},
        "anti-termite": {"matched_item": None},
    }

    def _price(self, **over):
        from neev_pipeline.tools.boq_analyst_tool import _price

        kwargs = dict(
            line_items=[
                {"id": "3.1", "desc": "RCC M25 for slab", "qty": 10, "unit": "cum",
                 "rate": 9800, "amount": 98000},
                {"id": "12.2", "desc": "MS main gate", "qty": 1, "unit": "no",
                 "rate": 18000, "amount": 18000},
            ],
            missing_scopes=["waterproofing"],
            built_up_sqft=1800,
            benchmarks=self.BENCH,
        )
        kwargs.update(over)
        return _price(**kwargs)

    def test_a_benchmarked_line_is_repriced_at_the_benchmark(self):
        out = self._price()
        # 10 cum of RCC at the benchmark, not at the quoted 9,800.
        self.assertLess(out["fair_price_for_quoted_scope"], 98000 + 18000)

    def test_an_unbenchmarked_line_keeps_its_quoted_amount(self):
        """Repricing an MS gate to zero would understate the fair price."""
        out = self._price(line_items=[
            {"id": "12.2", "desc": "MS main gate", "qty": 1, "unit": "no",
             "rate": 18000, "amount": 18000}])
        self.assertEqual(out["fair_price_for_quoted_scope"], 18000)

    def test_absent_scope_is_priced_with_a_quantity_and_a_rate(self):
        entry = self._price()["missing_scope"][0]
        self.assertEqual(entry["scope"], "waterproofing")
        self.assertGreater(entry["qty"], 0)
        self.assertGreater(entry["rate"], 0)
        self.assertAlmostEqual(entry["amount"], entry["qty"] * entry["rate"], delta=1)

    def test_the_total_is_the_sum_of_what_could_be_priced(self):
        out = self._price(missing_scopes=["waterproofing", "external plaster"])
        self.assertAlmostEqual(
            out["missing_scope_value"],
            sum(e["amount"] for e in out["missing_scope"] if e["amount"]),
            delta=1,
        )

    def test_scope_with_no_benchmark_is_reported_unpriced_not_as_zero(self):
        """anti-termite has no rate in the table, deliberately. Saying 0 would
        claim the missing work is free."""
        out = self._price(missing_scopes=["anti-termite"])
        entry = out["missing_scope"][0]
        self.assertIsNone(entry["amount"])
        self.assertIn("no benchmark", entry["note"].lower())

    def test_no_missing_scope_gives_a_zero_total_and_no_rows(self):
        out = self._price(missing_scopes=[])
        self.assertEqual(out["missing_scope"], [])
        self.assertEqual(out["missing_scope_value"], 0)


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


class TestBenchmarkTableIntegrity(unittest.TestCase):
    """rate_benchmarks.csv carries alias rows, so it needs two guards.

    Aliases exist because a contractor writes "damp proof course" where the
    table's keyword was only "dpc" -- 22 of 22 varied wordings went unbenchmarked
    before they were added. The cost of aliasing is duplicated rates, and these
    tests are what make that duplication safe.
    """

    @staticmethod
    def _rows():
        import csv
        path = os.path.join(
            os.path.dirname(__file__), "..", "fixtures", "rate_benchmarks.csv"
        )
        with open(path, newline="", encoding="utf-8") as handle:
            return list(csv.DictReader(handle))

    @staticmethod
    def _synthetic_boqs():
        sys.path.insert(
            0, os.path.join(os.path.dirname(__file__), "..", "scripts")
        )
        import synthetic_boqs

        return synthetic_boqs

    @staticmethod
    def _match(description, rows):
        """The tool's rule: substring match on keyword, longest wins."""
        hits = [r for r in rows if r["keyword"].lower() in description.lower()]
        return max(hits, key=lambda r: len(r["keyword"])) if hits else None

    def test_rows_sharing_a_description_agree_on_rate_and_unit(self):
        """Otherwise which synonym a contractor used would change the benchmark."""
        groups = {}
        for row in self._rows():
            groups.setdefault(row["description"], set()).add(
                (row["unit"], row["effective_rate"])
            )
        divergent = {d: v for d, v in groups.items() if len(v) > 1}
        self.assertEqual(divergent, {}, f"aliases disagree: {divergent}")

    def test_no_wording_is_matched_to_a_benchmark_in_a_different_unit(self):
        """The silent failure: comparing a per-cum quote to a per-sqm benchmark.

        check_rate_deviation divides one by the other without ever checking that
        the units agree, so a mismatch produces a confident, meaningless
        deviation. This asserts the table cannot route a wording that way.
        """
        synthetic_boqs = self._synthetic_boqs()

        rows = self._rows()
        mismatched = []
        for _section, base, alts, unit, _per_k, _kw in synthetic_boqs.TEMPLATE:
            for wording in (base, *alts):
                row = self._match(wording, rows)
                if row and row["unit"] != unit:
                    mismatched.append((wording, unit, row["keyword"], row["unit"]))
        self.assertEqual(mismatched, [], f"unit mismatches: {mismatched}")

    # Scope with no defensible rate anywhere. The table deliberately holds no
    # anti-termite benchmark: there is none in CPWD DSR 2023 and no sourced
    # market figure, and an invented one made the clean fixture's honest
    # Rs 95/sqm read as 21% under benchmark. It is caught by EXPECTED_SCOPE
    # (present or absent?), which needs no rate.
    LEGITIMATELY_UNBENCHMARKED = ("termite",)

    def test_every_realistic_wording_now_finds_a_benchmark(self):
        """22 of 66 wordings found nothing before the aliases were added."""
        synthetic_boqs = self._synthetic_boqs()

        rows = self._rows()
        unmatched = [
            wording
            for _s, base, alts, _u, _p, _k in synthetic_boqs.TEMPLATE
            for wording in (base, *alts)
            if self._match(wording, rows) is None
            and not any(w in wording.lower() for w in self.LEGITIMATELY_UNBENCHMARKED)
        ]
        self.assertEqual(unmatched, [], f"still unbenchmarked: {unmatched}")


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
