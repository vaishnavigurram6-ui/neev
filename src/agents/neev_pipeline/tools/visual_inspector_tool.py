# agents/neev_pipeline/tools/visual_inspector_tool.py
# Fixed: (1) generate_content was called BEFORE the prompt was defined and then
# again via an undefined `model` object — single correct call now; (2) model
# name comes from config; (3) stage names aligned with MILESTONE_WEIGHTS so
# downstream cumulative_weight() lookups never KeyError.

import json
import mimetypes
import pathlib

from google import genai
from google.genai import types

from ..config import GEMINI_MODEL

# Lazy, like the BigQuery clients in the sibling tools. At module scope this
# constructed a Gemini client on import, so `import neev_pipeline.agent` died
# without a key -- which is exactly what the backend's live runner does, and
# what scripts/record_golden_run.py does before it has read its arguments.
_genai = None


def _mime_for(path: str) -> str:
    """Best-effort content type for a local site photo.

    Gemini needs an explicit mime type on an inline part. Anything unguessable
    is treated as JPEG, which is what a phone or a WhatsApp export produces.
    """
    guessed, _ = mimetypes.guess_type(str(path))
    if not guessed and pathlib.Path(path).is_file():
        with pathlib.Path(path).open("rb") as handle:
            header = handle.read(12)
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if header.startswith(b"RIFF") and header[8:12] == b"WEBP":
            return "image/webp"
    return guessed if (guessed or "").startswith("image/") else "image/jpeg"


def _client():
    global _genai
    if _genai is None:
        _genai = genai.Client()  # reads GOOGLE_API_KEY from environment / .env
    return _genai

# Observable, checkable milestones per stage — grounds the model in specifics
# instead of asking it to guess a free-form percentage.
# Keys MUST match config.MILESTONE_WEIGHTS.
STAGE_CHECKLIST = {
    "foundation": [
        "Excavation visible or backfilled",
        "Foundation concrete/footing visible",
        "No plinth beam or columns above ground yet",
    ],
    "plinth": [
        "Plinth beam visible at ground level",
        "Backfilled and compacted up to plinth",
        "No columns/slab above plinth yet",
    ],
    "slab": [
        "Vertical columns visible",
        "Roof/floor slab cast or shuttering in place",
        "No exterior walls yet, or only partial",
    ],
    "brickwork_roof": [
        "Exterior walls visible in brick/block",
        "Window/door openings framed but not fitted",
        "Structure fully enclosed at this level",
    ],
    "finishing": [
        "Plastering visible on walls",
        "Doors/windows fitted",
        "Flooring or paint work visible",
    ],
}


def verify_construction_stage(image_paths: list[str], claimed_stage: str,
                              plan_summary: str = "") -> dict:
    """Analyzes 2-3 borrower-submitted site photos against a stage checklist and,
    optionally, cross-checks consistency with the approved building plan.

    Uses bucketed completion bands rather than a fabricated exact percentage,
    and flags low-confidence results for human review instead of auto-deciding.

    Args:
        image_paths: Local paths to 2-3 site photos (multiple
            angles increase reliability over a single photo).
        claimed_stage: Stage the borrower claims — one of foundation, plinth,
            slab, brickwork_roof, finishing.
        plan_summary: Optional short text summary of the approved plan
            (e.g. "G+1, RCC frame, 1500 sqft") for a plausibility check.
    Returns:
        dict with 'stage', 'checklist_results', 'completion_band',
        'matches_claim', 'plan_consistency', 'confidence',
        'needs_human_review', 'notes'.
    """
    if not image_paths:
        return _finalise({"confidence": "low", "needs_human_review": True,
                          "notes": "No site photos supplied."}, claimed_stage)
    if claimed_stage not in STAGE_CHECKLIST:
        raise ValueError(
            f"Unknown stage '{claimed_stage}'. Must be one of {list(STAGE_CHECKLIST)}")

    checklist = STAGE_CHECKLIST[claimed_stage]

    plan_instruction = (
        f'Approved plan summary: "{plan_summary}". Check only for clear '
        f'inconsistencies in scale/stage (e.g. plan specifies G+1 but photos show '
        f'a single-floor structure at "roof slab" stage) — do not flag minor '
        f'variations in framing or camera angle.'
        if plan_summary else
        "No plan summary provided — skip the plan consistency check and return "
        "\"not_checked\" for it."
    )

    prompt = f"""
You are inspecting {len(image_paths)} construction site photos (different angles
of the same site) against this checklist for the "{claimed_stage}" stage:
{checklist}

For each checklist item, mark it CLEARLY VISIBLE, PARTIALLY VISIBLE, or NOT
VISIBLE, using evidence across all photos together.

Then estimate stage completion using ONLY these bands based on how many items
are clearly visible: "0-25%", "25-50%", "50-75%", "75-100%". Do NOT invent an
exact percentage — bands only; that is the honest precision a photo supports.

{plan_instruction}

If photos are unclear, poorly lit, contradict each other, or you are not
confident, set "needs_human_review" to true rather than guessing.

Respond ONLY in JSON:
{{
  "observed_stage": "foundation / plinth / slab / brickwork_roof / finishing / not_assessed",
  "checklist_results": {{"<item>": "CLEARLY VISIBLE / PARTIALLY VISIBLE / NOT VISIBLE"}},
  "completion_band": "0-25% | 25-50% | 50-75% | 75-100%",
  "matches_claim": true,
  "plan_consistency": "consistent / inconsistent / not_checked",
  "confidence": "high/medium/low",
  "needs_human_review": false,
  "notes": "brief explanation referencing what was/wasn't visible"
}}
"""

    # Inline bytes, not the Files API. client.files.upload() raises
    # "This method is only supported in the Gemini Developer client" on Vertex,
    # which is the keyless route this project authenticates through -- so the
    # upload path made the whole inspector unusable there. Inline parts work on
    # both backends and need no intermediate upload at all.
    parts = [types.Part.from_text(text=prompt)]
    for path in image_paths:
        data = pathlib.Path(path).read_bytes()
        parts.append(
            types.Part.from_bytes(
                data=data, mime_type=_mime_for(path)
            )
        )
    response = _client().models.generate_content(
        model=GEMINI_MODEL,
        contents=[types.Content(role="user", parts=parts)],
    )
    text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
    result = json.loads(text)

    return _finalise(result, claimed_stage)


def _finalise(result: dict, claimed_stage: str) -> dict:
    """Normalise the model's reply. Pure, so it is testable without a call.

    `stage` used to be assigned claimed_stage unconditionally, which meant the
    stage every downstream calculation trusted was the borrower's claim rather
    than anything observed -- the verification was cosmetic. It now reports what
    was seen, and requires human review when no valid observation is supplied.
    """
    result = dict(result)

    observed = result.get("observed_stage") or result.get("stage")
    valid = observed in STAGE_CHECKLIST
    confidence = result.get("confidence")
    if confidence == "med":
        confidence = "medium"
    if confidence not in ("high", "medium", "low"):
        confidence = "low"
    result["confidence"] = confidence
    result["stage"] = observed if valid else "not_assessed"
    result["matches_claim"] = (
        valid and observed == claimed_stage and result.get("matches_claim") is True
        and result.get("plan_consistency") != "inconsistent"
    )
    result["needs_human_review"] = (
        result.get("needs_human_review") is not False or not valid
        or confidence == "low" or not result["matches_claim"]
    )
    result["claimed_stage"] = claimed_stage
    return result
