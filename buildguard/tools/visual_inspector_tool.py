# buildguard/tools/visual_inspector_tool.py
# Fixed: (1) generate_content was called BEFORE the prompt was defined and then
# again via an undefined `model` object — single correct call now; (2) model
# name comes from config; (3) stage names aligned with MILESTONE_WEIGHTS so
# downstream cumulative_weight() lookups never KeyError.

import json
from google import genai

from ..config import GEMINI_MODEL

client = genai.Client()  # reads GOOGLE_API_KEY from environment / .env

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
        image_paths: Local paths or GCS URIs to 2-3 site photos (multiple
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
  "checklist_results": {{"<item>": "CLEARLY VISIBLE / PARTIALLY VISIBLE / NOT VISIBLE"}},
  "completion_band": "0-25% | 25-50% | 50-75% | 75-100%",
  "matches_claim": true,
  "plan_consistency": "consistent / inconsistent / not_checked",
  "confidence": "high/medium/low",
  "needs_human_review": false,
  "notes": "brief explanation referencing what was/wasn't visible"
}}
"""

    image_files = [client.files.upload(file=p) for p in image_paths]
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[prompt, *image_files],
    )
    text = response.text.strip().removeprefix("```json").removesuffix("```").strip()
    result = json.loads(text)

    # Belt-and-braces: force human review on low confidence even if the model
    # forgot to flag it.
    if result.get("confidence") == "low":
        result["needs_human_review"] = True
    result["stage"] = claimed_stage
    return result
