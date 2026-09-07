"""The parse layer, exercised against text shaped like a real model response.

Every input here is raw text of the kind an ADK `output_key` actually holds --
fenced, prose-wrapped, missing the presentation fields the agent prompts never
ask for. No credentials, no network, no ADK: the whole point is that getting the
parse right costs nothing, so a captured run can afford to be wrong on the first
try. See scripts/record_golden_run.py.
"""

import json

import pytest

from app.schemas.pipeline import PipelineOutput
from app.services.pipeline_parse import (
    _normalize_flag,
    extract_json,
    normalize,
    parse_output_key,
    parse_state,
)

# --------------------------------------------------------------- extract_json


def test_extract_json_strips_a_fenced_code_block():
    raw = '```json\n{"boq_total": 100}\n```'
    assert extract_json(raw) == {"boq_total": 100}


def test_extract_json_ignores_prose_around_the_object():
    raw = 'Here is my analysis:\n{"boq_total": 100}\nHope that helps.'
    assert extract_json(raw) == {"boq_total": 100}


def test_extract_json_passes_a_dict_through_untouched():
    assert extract_json({"boq_total": 100}) == {"boq_total": 100}


def test_extract_json_reports_the_text_when_there_is_no_object():
    with pytest.raises(ValueError, match="No JSON object"):
        extract_json("I could not read the document.")


# ------------------------------------------------------- flag normalization
# The agent prompt asks for {item, type, evidence, question} and nothing else
# (src/agents/neev_pipeline/agent.py). `label` is required by the schema, so
# without derivation every real flag fails validation.


def _flag(**over):
    flag = {
        "item": "3.1",
        "type": "RATE_OUTLIER",
        "evidence": "Quoted 8600 against a benchmark of 7050.",
        "question": "Could you share the rate basis for this item?",
    }
    flag.update(over)
    return flag


def _findings(*flags):
    return {
        "line_items": [],
        "flags": list(flags),
        "boq_total": 4_182_000,
        "payment_pct_before_slab": 0.45,
    }


def test_rate_outlier_label_quotes_the_deviation():
    out = normalize("boq_findings", _findings(_flag(deviation_pct=22.0)))
    assert out["flags"][0]["label"] == "Rate +22%"


def test_rate_outlier_label_keeps_the_sign_of_a_negative_deviation():
    out = normalize("boq_findings", _findings(_flag(deviation_pct=-9.0)))
    assert out["flags"][0]["label"] == "Rate -9%"


def test_rate_outlier_without_a_deviation_falls_back_to_a_bare_label():
    out = normalize("boq_findings", _findings(_flag()))
    assert out["flags"][0]["label"] == "Rate outlier"


def test_underspecified_flag_about_a_grade_is_labelled_no_grade():
    flag = _flag(
        type="UNDERSPECIFIED",
        evidence="No grade stated. Fe 415 vs Fe 500 changes the tonnage needed.",
    )
    out = normalize("boq_findings", _findings(flag))
    assert out["flags"][0]["label"] == "No grade"


def test_underspecified_flag_about_a_brand_is_labelled_vague_spec():
    flag = _flag(type="UNDERSPECIFIED", evidence="No brand or model named.")
    out = normalize("boq_findings", _findings(flag))
    assert out["flags"][0]["label"] == "Vague spec"


@pytest.mark.parametrize(
    ("flag_type", "label", "tone"),
    [
        ("MISSING_SCOPE", "Missing", "danger"),
        ("GST_SILENT", "GST unclear", "warn"),
        ("STEEL_RATIO", "Steel ratio", "warn"),
        ("FRONT_LOADED", "Front-loaded", "danger"),
        ("UNBENCHMARKED", "No benchmark", "neutral"),
    ],
)
def test_every_flag_type_derives_a_label_and_a_tone(flag_type, label, tone):
    out = normalize("boq_findings", _findings(_flag(type=flag_type)))
    assert out["flags"][0]["label"] == label
    assert out["flags"][0]["tone"] == tone


def test_a_label_the_model_supplied_is_never_overwritten():
    out = normalize("boq_findings", _findings(_flag(label="Rate way off")))
    assert out["flags"][0]["label"] == "Rate way off"


def test_normalization_leaves_an_unknown_flag_type_alone_for_the_schema_to_reject():
    """Inventing a label for a type the schema forbids would hide the failure."""
    out = normalize("boq_findings", _findings(_flag(type="VIBES_OFF")))
    assert "label" not in out["flags"][0]


# ----------------------------------------------- cost_estimate normalization
# estimate_construction_cost returns `estimated_cost`; the schema wants
# `expected_total_cost`. The prompt asks the model to rename it, which is a
# thing models forget.


def test_cost_estimate_accepts_the_tools_own_field_name():
    out = normalize("cost_estimate", {"estimated_cost": 5_100_000})
    assert out["expected_total_cost"] == 5_100_000


def test_cost_estimate_prefers_the_schema_name_when_both_are_present():
    out = normalize(
        "cost_estimate", {"estimated_cost": 1, "expected_total_cost": 5_100_000}
    )
    assert out["expected_total_cost"] == 5_100_000


# -------------------------------------------------------- parse_output_key


def test_parse_output_key_validates_fenced_text_into_a_model():
    raw = "```json\n" + json.dumps(_findings(_flag(deviation_pct=18.0))) + "\n```"
    findings = parse_output_key("boq_findings", raw)
    assert findings.flags[0].label == "Rate +18%"
    assert findings.boq_total == 4_182_000


# -------------------------------------------------------------- parse_state


def _state():
    return {
        "boq_findings": json.dumps(_findings(_flag(deviation_pct=22.0))),
        "cost_estimate": json.dumps(
            {"estimated_cost": 5_100_000, "completed_value_estimate": 2_040_000}
        ),
        "inspection_result": json.dumps(
            {"stage": "slab", "confidence": "high", "matches_claim": True}
        ),
        "risk_assessment": json.dumps(
            {
                "exposure_ratio": 0.88,
                "recommendation": "RELEASE",
                "pct_complete": 0.5,
                "verified_value": 2_040_000,
                "cost_to_complete_gap": 120_000,
            }
        ),
        "explanation": json.dumps(
            {"owner_view": "Three rates look high.", "officer_view": "Exposure 0.88."}
        ),
    }


def test_parse_state_builds_a_pipeline_output_from_all_five_keys():
    result = parse_state(_state())
    assert result.errors == {}
    assert isinstance(result.output, PipelineOutput)
    assert result.output.cost_estimate.expected_total_cost == 5_100_000


def test_parse_state_records_a_bad_key_instead_of_raising():
    """One malformed key must not discard the four that cost the same money."""
    state = _state() | {"risk_assessment": "the model refused to answer"}
    result = parse_state(state)
    assert "risk_assessment" in result.errors
    assert result.parsed["boq_findings"]["boq_total"] == 4_182_000


def test_parse_state_reports_every_bad_key_not_just_the_first():
    state = _state() | {"cost_estimate": "nope", "explanation": "also nope"}
    result = parse_state(state)
    assert set(result.errors) == {"cost_estimate", "explanation"}


def test_parse_state_notes_an_absent_key():
    state = _state()
    del state["explanation"]
    result = parse_state(state)
    assert "explanation" in result.errors
    assert result.output is None


def test_parse_state_omits_an_optional_key_that_is_absent():
    """A loan with no photos has no inspection_result, and that is valid."""
    state = _state()
    del state["inspection_result"]
    result = parse_state(state)
    assert result.errors == {}
    assert result.output is not None
    assert result.output.inspection_result is None


# ------------------------------------------------------------- base merging
# payment_schedule has no output_key -- it is read from the document, not
# emitted by an agent -- and cost_estimate.sections needs reasoning the prompt
# may not supply. Neither may be lost by capturing a run.


def test_parse_state_keeps_a_base_value_the_pipeline_does_not_own():
    base = {"payment_schedule": [{"label": "On signing", "pct": 0.1, "before_slab": True}]}
    result = parse_state(_state(), base=base)
    assert result.parsed["payment_schedule"] == base["payment_schedule"]


def test_parse_state_keeps_base_sections_when_the_run_supplies_none():
    """A shallow merge would drop all five authored sections."""
    base = {"cost_estimate": {"sections": [{"name": "Steel", "delta": -84_000}]}}
    result = parse_state(_state(), base=base)
    assert result.parsed["cost_estimate"]["sections"] == base["cost_estimate"]["sections"]
    assert result.parsed["cost_estimate"]["expected_total_cost"] == 5_100_000


def test_a_captured_section_wins_over_the_authored_one():
    base = {"cost_estimate": {"sections": [{"name": "Steel", "delta": -84_000}]}}
    state = _state() | {
        "cost_estimate": json.dumps(
            {
                "estimated_cost": 5_100_000,
                "completed_value_estimate": 2_040_000,
                "sections": [{"name": "RCC", "delta": -120_000}],
            }
        )
    }
    result = parse_state(state, base=base)
    assert [s["name"] for s in result.parsed["cost_estimate"]["sections"]] == ["RCC"]


# --------------------------------------------------- correspondence with the
# authored fixtures. This is the test that makes the capture a swap rather than
# a migration: if derivation stopped reproducing the labels the mockups use, a
# recorded run would quietly restyle every pill on BoQ Review.


def test_derived_labels_and_tones_reproduce_the_authored_fixtures():
    from app.fixtures.loader import available_loan_ids, load_pipeline_output

    checked = 0
    for loan_id in available_loan_ids():
        authored = load_pipeline_output(loan_id).boq_findings
        for flag in authored.flags:
            stripped = flag.model_dump(mode="json", exclude_none=True)
            del stripped["label"], stripped["tone"]
            derived = _normalize_flag(stripped)
            assert derived["label"] == flag.label, f"{loan_id} {flag.item}"
            assert derived["tone"] == flag.tone, f"{loan_id} {flag.item}"
            checked += 1
    assert checked, "no authored flags found -- the guard would pass vacuously"


# ------------------------------------------------- what the first real run said
# Every case below is taken verbatim from .golden_runs/1001-20260907T155507Z.json,
# the first captured run. None of it was anticipated by the authored fixtures.


def test_a_flag_type_the_model_renamed_is_mapped_to_the_canonical_one():
    """The real run emitted PAYMENT_SCHEDULE where FlagType says FRONT_LOADED."""
    flag = _flag(type="PAYMENT_SCHEDULE", evidence="45% due before the slab.")
    out = normalize("boq_findings", _findings(flag))
    assert out["flags"][0]["type"] == "FRONT_LOADED"
    assert out["flags"][0]["label"] == "Front-loaded"


def test_an_unrecognised_flag_type_is_still_left_to_fail():
    """Aliasing must not become a licence to invent categories."""
    out = normalize("boq_findings", _findings(_flag(type="VIBES_OFF")))
    assert out["flags"][0]["type"] == "VIBES_OFF"
    assert "label" not in out["flags"][0]


def test_evidence_notes_given_as_prose_becomes_a_one_item_list():
    """The real run returned a sentence where the schema wants list[str]."""
    out = normalize(
        "inspection_result",
        {"stage": "slab", "confidence": "high", "matches_claim": True,
         "evidence_notes": "Slab shuttering visible."},
    )
    assert out["evidence_notes"] == ["Slab shuttering visible."]


def test_an_inspection_that_could_not_assess_anything_is_not_an_inspection():
    """confidence 'none' + matches_claim null is the model saying "I couldn't".

    PipelineOutput already models that as an absent inspection_result, which is
    truer than coercing it into a low-confidence one that implies a judgement
    nobody made.
    """
    state = _state() | {
        "inspection_result": json.dumps({
            "stage": "not_assessed", "confidence": "none", "matches_claim": None,
            "evidence_notes": "No site photos were supplied.",
        })
    }
    result = parse_state(state)
    assert result.errors == {}
    assert result.output is not None
    assert result.output.inspection_result is None


def test_a_required_key_that_cannot_be_assessed_is_still_an_error():
    """The leniency above applies only to keys PipelineOutput marks optional."""
    state = _state() | {"boq_findings": json.dumps({"unassessable": True})}
    result = parse_state(state)
    assert "boq_findings" in result.errors


def test_an_explicitly_null_captured_field_is_not_back_filled_from_base():
    """The first real run produced a self-contradictory record this way.

    assess_tranche returned exposure_ratio null with exposure_undefined true --
    "I cannot compute this". model_dump(exclude_none=True) drops the null, which
    made it indistinguishable from a field the model never mentioned, so the
    authored base's 1.29 was merged back in. The stored result then claimed both
    that exposure was undefined AND that it was 1.29.
    """
    base = {"risk_assessment": {"exposure_ratio": 1.29, "verified_value": 1_390_000}}
    state = _state() | {
        "risk_assessment": json.dumps({
            "exposure_ratio": None, "exposure_undefined": True,
            "recommendation": "INSPECT", "pct_complete": 0.0,
            "verified_value": 0, "cost_to_complete_gap": -435_794,
        })
    }
    result = parse_state(state, base=base)
    assert result.parsed["risk_assessment"]["exposure_undefined"] is True
    assert result.parsed["risk_assessment"].get("exposure_ratio") is None
    assert result.parsed["risk_assessment"]["verified_value"] == 0
