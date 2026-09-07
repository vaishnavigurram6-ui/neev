# Raw captured pipeline runs

Each file is the ADK session state from one real run of the five-agent pipeline,
saved **before** any parsing — so a run that later failed validation is still
here in full. `scripts/record_golden_run.py --from-raw <file>` re-parses one at
no cost, which is how the parse layer was debugged without paying twice.

Contents are the five `output_key` values as the agents left them: raw model
text, usually a fenced JSON block. No credentials.

## Which ones matter

| File | What it shows |
|---|---|
| `1001-20260907T165614Z.json` | **Serving now.** The run behind loan 1001's screens: HOLD at exposure 1.11 |
| `1002-20260907T165921Z.json` | **Serving now.** Loan 1002: RELEASE at 0.82 |
| `1002-20260907T162216Z.json` | The G+1 catch — `matches_claim: false`, *"the photo shows a G+1 structure, which contradicts the approved plan summary for a G+0 building"* |
| `1002-20260907T162846Z.json` | The **same two photos**, `matches_claim: true`. The pair is the honest evidence that the plan-consistency check is a model judgement and varies |

The rest are earlier attempts, kept because they document real defects rather
than noise:

- `1001-20260907T155507Z.json` — the very first complete run, and the one that
  found three things no authored fixture had: the model naming a flag type
  `PAYMENT_SCHEDULE` where `FlagType` says `FRONT_LOADED`, `evidence_notes`
  written as a sentence where the schema wants `list[str]`, and
  `confidence: "none"` for a stage it honestly could not judge. All three are
  handled in `app/services/pipeline_parse.py` because of this file
- `1001-20260907T160416Z.json` — before the prompt required `deviation_pct`, so
  every rate flag degraded to a bare "Rate outlier"
- `1001-20260907T161515Z.json` — carries a `_run_failure` key. The Files API is
  not supported on Vertex, so `verify_construction_stage` raised mid-pipeline;
  the guard in `capture()` saved what the session held rather than losing the
  spend
- `1001-20260907T161902Z.json`, `1002-20260907T160721Z.json` — runs with no
  photos, where the inspector correctly reported it could not assess a stage and
  `assess_tranche` returned INSPECT with exposure undefined

## Reproducing

Needs the dry run lifted, and costs roughly ₹4 per run:

```bash
export GOOGLE_CLOUD_PROJECT=buildguard-ai-2026 GOOGLE_CLOUD_LOCATION=global
export GOOGLE_GENAI_USE_VERTEXAI=true NEEV_ALLOW_BILLED_CALLS=1
src/agents/.venv/bin/python scripts/record_golden_run.py --loan 1001 \
  --boq fixtures/sample_boq.pdf --photos demo_assets/*.jpeg
```

`GOOGLE_CLOUD_LOCATION=global` is not optional: `gemini-3.6-flash` is not served
from `asia-south1`.
