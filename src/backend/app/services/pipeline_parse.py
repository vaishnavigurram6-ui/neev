"""Turns a finished ADK run into a PipelineOutput. Spec §4.3, deferred by §4.4a.

The five `output_key` values arrive in ADK session state as raw model TEXT --
usually a fenced JSON block, sometimes with prose around it -- and they carry
only the fields the agent instructions ask for. Two of the schema's required
fields are not among them:

  * `Flag.label`  -- boq_analyst_agent is told to emit {item, type, evidence,
    question} and nothing else, so every real flag would fail validation.
  * `cost_estimate.expected_total_cost` -- estimate_construction_cost returns
    it as `estimated_cost` and the prompt asks the model to rename it, which is
    a thing models forget.

So this module extracts, normalizes, then validates. Deriving `label` and
`tone` from `type` is deterministic and free; asking the model for display
strings spends tokens on a dict lookup and can drift between runs. The derived
values reproduce the conventions the authored fixtures already use, which is
what lets test_fixture_contract keep passing across the swap.

Nothing here imports the ADK or touches the network: the parse layer is fully
testable offline, so one paid capture can be re-parsed for free until it is
right. `scripts/record_golden_run.py --from-raw` is that loop.
"""

import json
import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ValidationError

from app.schemas.pipeline import (
    BoqFindings,
    CostEstimate,
    Explanation,
    InspectionResult,
    PipelineOutput,
    RiskAssessment,
)

# The five agent output_keys, in pipeline order, and the model each must satisfy.
OUTPUT_KEY_MODELS: dict[str, type[BaseModel]] = {
    "boq_findings": BoqFindings,
    "cost_estimate": CostEstimate,
    "inspection_result": InspectionResult,
    "risk_assessment": RiskAssessment,
    "explanation": Explanation,
}

# PipelineOutput allows these to be absent: a loan that has not requested a
# tranche has no inspection and no risk assessment. Their absence is a fact
# about the loan, not a parse failure.
OPTIONAL_KEYS = frozenset({"inspection_result", "risk_assessment"})

# Has no output_key at all -- the payment schedule is read off the document
# rather than emitted by an agent -- so a capture must never overwrite it.
UNOWNED_KEYS = frozenset({"payment_schedule"})

# Flag tone by type. Presentation-independent: the theme resolves the colour.
FLAG_TONES: dict[str, str] = {
    "RATE_OUTLIER": "danger",
    "MISSING_SCOPE": "danger",
    "FRONT_LOADED": "danger",
    "UNDERSPECIFIED": "warn",
    "GST_SILENT": "warn",
    "STEEL_RATIO": "warn",
    "UNBENCHMARKED": "neutral",
}

# "No grade" vs "Vague spec": the finding must ASSERT a missing grade, so the
# negation has to sit right before the word. Fixture 1001/9.1 mentions "FR
# grade" only in its remedy and must stay "Vague spec".
_MISSING_GRADE = re.compile(
    r"\b(?:no|not|without|missing|unspecified)\s+(?:\w+\s+){0,1}grade\b", re.I
)

# Flag pill label by type, for the types whose label is fixed. RATE_OUTLIER and
# UNDERSPECIFIED are computed instead -- see _flag_label.
FLAG_LABELS: dict[str, str] = {
    "MISSING_SCOPE": "Missing",
    "GST_SILENT": "GST unclear",
    "STEEL_RATIO": "Steel ratio",
    "FRONT_LOADED": "Front-loaded",
    "UNBENCHMARKED": "No benchmark",
}


@dataclass
class ParseResult:
    """What one capture yielded, and what went wrong.

    `errors` is keyed by output_key so a failed run says everything that is
    wrong at once. `output` is None whenever anything required is missing, but
    `parsed` still holds every key that did validate -- the run cost money, so
    nothing usable is thrown away.
    """

    parsed: dict[str, Any] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)
    output: PipelineOutput | None = None


def extract_json(raw: object) -> dict:
    """Pull the JSON object out of a model response.

    Handles a fenced block, a bare object, and prose either side of one. Raises
    ValueError with a slice of the text when there is no object at all, because
    the text is the only evidence of what the model actually said.
    """
    if isinstance(raw, dict):
        return raw

    text = str(raw).strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) > 1:
            text = parts[1]
            if text.lower().startswith("json"):
                text = text[4:]

    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"No JSON object found in: {text[:200]}")
    return json.loads(text[start : end + 1])


def _flag_label(flag: dict) -> str | None:
    """The pill label for one flag, or None if the type is not one we know.

    An unrecognised type gets no label, so the schema's FlagType rejects it
    instead of the flag slipping through wearing an invented one.
    """
    flag_type = flag.get("type")

    if flag_type == "RATE_OUTLIER":
        deviation = flag.get("deviation_pct")
        if deviation is None:
            return "Rate outlier"
        return f"Rate {float(deviation):+.0f}%"

    if flag_type == "UNDERSPECIFIED":
        # The prompt separates "no grade (e.g. TMT without Fe500)" from a
        # missing brand or IS standard, and the mockups label them differently.
        # The word alone will not do: fixture 1001/9.1 reads '"Branded" names no
        # brand. Specify make and FR grade.' -- "grade" there is the remedy, not
        # the finding. So require a negation right before it.
        evidence = str(flag.get("evidence", ""))
        stated_missing = _MISSING_GRADE.search(evidence)
        return "No grade" if stated_missing else "Vague spec"

    return FLAG_LABELS.get(flag_type)


def _normalize_flag(flag: dict) -> dict:
    flag = dict(flag)
    if "label" not in flag:
        label = _flag_label(flag)
        if label is not None:
            flag["label"] = label
    if "tone" not in flag:
        tone = FLAG_TONES.get(flag.get("type"))
        if tone is not None:
            flag["tone"] = tone
    return flag


def normalize(key: str, obj: dict) -> dict:
    """Fill in the schema fields the agent instructions never ask for.

    Only ever adds what is absent: a value the model did supply is authoritative,
    including one we would have derived differently.
    """
    obj = dict(obj)

    if key == "boq_findings" and isinstance(obj.get("flags"), list):
        obj["flags"] = [
            _normalize_flag(f) if isinstance(f, dict) else f for f in obj["flags"]
        ]

    if key == "cost_estimate" and "expected_total_cost" not in obj:
        if "estimated_cost" in obj:
            obj["expected_total_cost"] = obj["estimated_cost"]

    return obj


def _parse_one(key: str, raw: object) -> tuple[BaseModel, set[str]]:
    """Validate one output_key, and report which fields the capture spoke to.

    The second element is what makes the merge in parse_state honest. It cannot
    be read off the validated model: a field with `default_factory=list` dumps
    as `[]` whether the model returned an empty list or never mentioned it, and
    those two mean opposite things when a base value exists.
    """
    normalized = normalize(key, extract_json(raw))
    return OUTPUT_KEY_MODELS[key].model_validate(normalized), set(normalized)


def parse_output_key(key: str, raw: object) -> BaseModel:
    """Extract, normalize and validate one output_key. Raises on failure."""
    return _parse_one(key, raw)[0]


def parse_state(state: dict, *, base: dict | None = None) -> ParseResult:
    """Parse a whole ADK session state into a PipelineOutput.

    `base` is the fixture being replaced, if any. Fields it holds that the
    pipeline does not emit survive the capture: `payment_schedule`, which no
    agent owns, and per-key fields a run happened not to supply --
    `cost_estimate.sections`, for instance, which feeds Sanction Check's
    "where the gap comes from" table and needs reasoning the prompt may not
    have produced. A captured value always wins over a base one.
    """
    base = base or {}
    result = ParseResult()

    for key in OUTPUT_KEY_MODELS:
        raw = state.get(key)
        if raw is None:
            if key not in OPTIONAL_KEYS:
                result.errors[key] = "absent from session state"
            continue
        try:
            parsed, spoke_to = _parse_one(key, raw)
        except (ValidationError, ValueError, json.JSONDecodeError) as exc:
            result.errors[key] = str(exc)
            continue
        captured = parsed.model_dump(mode="json", exclude_none=True)
        # Per-key merge, not a top-level one: a shallow {**base, **captured}
        # over whole output_keys drops every authored field the run omitted.
        # Restricting to the fields the capture spoke to is what lets a base
        # value survive -- cost_estimate.sections being the case that matters.
        result.parsed[key] = {
            **base.get(key, {}),
            **{k: v for k, v in captured.items() if k in spoke_to},
        }

    for key in UNOWNED_KEYS:
        if key in base:
            result.parsed[key] = base[key]

    if not result.errors:
        try:
            result.output = PipelineOutput.model_validate(result.parsed)
        except ValidationError as exc:
            result.errors["pipeline_output"] = str(exc)

    return result
