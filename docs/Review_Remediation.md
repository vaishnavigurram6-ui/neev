# Review remediation — 2026-09-08

## Status and scope

Keep the three-package layout. **Demo-hardened is not live-validated or production-ready.**
This document supersedes older claims of complete live integration, anonymous API
access, fixed mockup financial figures, and destructive reset-on-start behavior.

### Implemented

- Inspection requires an observed stage. Missing photos, invalid confidence,
  contradictory evidence and human-review flags cannot justify RELEASE.
- Risk arithmetic includes requested funds in projected exposure and checks the
  sanction ceiling. Existing exposure and projected exposure remain distinct.
- Rate comparisons convert explicit compatible units; incompatible/missing units
  remain unassessable. Unpriced amounts are not verified benchmark matches.
- Section delta is **market minus quoted**, derived when both amounts exist.
  Unknown quoted amounts cannot be counted as negotiation savings.
- Private API reads/writes require signed, expiring sessions and loan/role
  authorization, including job status and SSE. Frontend requests forward identity.
  Local/offline session fabrication and role-switch cookie rewriting are removed.
- Demo sign-in is **disabled by default**. Local dev explicitly enables it with
  NEEV_DEMO_AUTH=true. Signing protects integrity, NOT borrower identity: a demo
  visitor still chooses a role. Restarting the single backend invalidates sessions.
- BoQs and site images persist in private local artifacts with random names and
  restricted permissions. Files are limited to 10 MB; images are decoded and
  verified; PDF envelopes are checked. No spreadsheet parser is promised.
- Submitted stages are claims, never observations. New photos require review and
  do not increase verified value. Artifacts are not publicly served.
- Runner results are explicit. Validation and database commit precede success;
  missing results/save failures produce error then terminal events. Raw exception
  text is not exposed to clients.
- Questions belong to revisions; sending the latest questions leaves old versions
  untouched. Request context binds risk snapshots to the assessed tranche.
- Decision events are append-only. The old Decision table is a latest-state
  projection. Idempotency-Key deduplicates API retries; conflicting reuse is 409.
  Decisions still do not perform disbursements.
- All-items shows every stored document line. Unflagged means no recorded finding,
  not a benchmark match. Provisional benchmarks and demo replay are labeled.
- New captures retain per-field provenance for authored fallbacks. Legacy captures
  without that metadata are labeled unknown rather than retroactively rewritten.
- Portfolio action counts include HOLD/INSPECT/ESCALATE. Completion shortfalls
  are no longer described as over-disbursement, and visit savings are not invented.
- OpenAPI and response TypeScript contracts generate offline with existing Python
  dependencies. Unsupported schema shapes fail explicitly. UI imports generated
  contracts; npm run verify checks drift locally. Frontend tests cover uploads
  and SSE failure/replay.
- Additive demo DB migration preserves legacy questions. Startup initializes and
  seeds only an empty book; it does not reset an existing database.

## Running and checking locally

- Start: bash scripts/dev.sh (synthetic/demo data only).
- Agent tools: python3 -m unittest tests.test_offline tests.test_review_safety -q
- Backend: from src/backend, .venv/bin/python -m pytest tests/ -q
- Frontend: from src/frontend, npm run gen:types followed by npm run verify.
- Existing local databases are upgraded by app.db.seed / init_db; no manual reset
  is needed. Uploads remain in src/backend/artifacts unless ARTIFACT_DIR is set.
- Fixture mode **replays the stored sample**, regardless of upload contents. A new
  upload is retained, but the replay must not be represented as its analysis.

### Final local verification (2026-09-08)

- Offline agent/tool suite: **70 passed**, exit 0.
- Backend suite: **196 passed**, exit 0; outbound sockets blocked by test fixtures.
- Frontend verify: contract drift, typecheck, **4 behavioral tests**, lint, theme
  check and production build all passed, exit 0.
- Python compilation, shell syntax and git diff whitespace checks passed.
- Non-blocking warnings: Starlette TestClient/httpx deprecation and Node's
  module-type inference warning for TypeScript test imports. No dependency
  versions were changed to suppress these warnings.
- GitHub Actions CI is intentionally omitted at the owner's request; the local
  verification commands remain available. No browser/container smoke test,
  Gemini execution, or deployment was performed.

## Remaining gates — do not use with real borrower data yet

1. **Production identity:** verified OTP/SSO, server-derived role/loan assignments,
   session revocation/shared keys, CSRF/rate controls and secure deployment IAM.
2. **Live validation:** the live request now includes document bytes, evidence
   references and draw context. Gemini execution is still untested and gated.
   The fixture-only backend image intentionally has no agent dependencies; changing
   environment variables alone does not enable it. A dedicated live image and
   owner-approved integration run are required, including tool/evidence provenance.
3. **Durability:** durable job queue, retained object storage, production migration
   tooling, backup/restore and concurrency-safe revision/idempotency constraints.
   Local artifacts and SQLite on Cloud Run remain ephemeral. Orphan artifact
   cleanup/retention and download authorization are not implemented.
4. **Evidence assurance:** approved-plan linkage, image authenticity/geotag checks,
   evidence-set versioning, stale-result rejection and auditor access to decision
   history. Claimed progress alone is never enough to release funds.
5. **Financial authority:** independently verify the 62 benchmark rows, date and
   source each rate, define assessed/matched item coverage, and validate the
   lending policy with domain experts. Seeded historical values are demo records.
6. **Operations:** reproducible Python dependency lock, observability, upload-body
   limits at the proxy before multipart parsing, PDF structural/malware scanning,
   cross-browser UI tests and actual deployment/container smoke testing.

The deployment script refuses unless NEEV_DEPLOY_SANDBOX=1 is explicitly set.
That acknowledgment is **not deployment approval**. Each Cloud Run deployment
and every Gemini run still requires the owner's separate approval under AGENTS.md.