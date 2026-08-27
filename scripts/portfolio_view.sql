-- portfolio_hotlist — Beat 4: the lender's portfolio screen.
-- One row per loan (latest tranche), scored with the same exposure math as
-- disbursal_risk_tool, sorted worst-first by cost-to-complete gap.
--
-- HONESTY NOTE: this is a SCREEN, not the per-loan verdict. It uses the
-- sanctioned amount as a proxy for expected_total_cost (the real pipeline
-- computes expected cost from the BoQ + benchmarks per loan). Loans surfaced
-- here get the full 5-agent run before any action.
--
-- CASE weights are the CUMULATIVE milestone weights from agents/neev_pipeline/config.py
-- (MILESTONE_WEIGHTS); tests/test_offline.py asserts they stay in sync.
--
-- __PROJECT__ is substituted by scripts/load_bigquery.sh.

CREATE OR REPLACE VIEW `__PROJECT__.buildguard_data.portfolio_hotlist` AS
WITH latest AS (
  SELECT
    *,
    ROW_NUMBER() OVER (PARTITION BY loan_id ORDER BY tranche_no DESC) AS rn
  FROM `__PROJECT__.buildguard_data.draw_schedule`
),
scored AS (
  SELECT
    loan_id,
    tranche_no,
    inspection_date,
    observed_stage,
    sanctioned,
    disbursed_cum,
    CASE observed_stage  -- cumulative_weight(stage) from config.py
      WHEN 'foundation'     THEN 0.15
      WHEN 'plinth'         THEN 0.25
      WHEN 'slab'           THEN 0.50
      WHEN 'brickwork_roof' THEN 0.80
      WHEN 'finishing'      THEN 1.00
    END AS verified_pct
  FROM latest
  WHERE rn = 1
)
SELECT
  loan_id,
  tranche_no,
  inspection_date,
  observed_stage,
  sanctioned,
  disbursed_cum,
  verified_pct,
  ROUND(SAFE_DIVIDE(disbursed_cum, sanctioned * verified_pct), 2) AS exposure_ratio,
  CAST((sanctioned - disbursed_cum) - sanctioned * (1 - verified_pct) AS INT64)
    AS cost_to_complete_gap,
  CASE
    WHEN verified_pct IS NULL THEN 'ESCALATE'  -- unknown stage: never auto-release
    WHEN SAFE_DIVIDE(disbursed_cum, sanctioned * verified_pct) > 1.0 THEN 'REVIEW'
    ELSE 'OK'
  END AS screen_status
FROM scored
ORDER BY cost_to_complete_gap ASC, exposure_ratio DESC;
