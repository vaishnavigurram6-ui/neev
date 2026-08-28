// The view models the screens consume, mirroring `app/schemas/views.py` on the
// backend field for field.
//
// Hand-transcribed rather than generated: `npm run gen:types` derives these from
// the backend's OpenAPI schema, and `src/backend/` does not exist in this
// worktree yet. The script is wired up in package.json — run it once the backend
// lands and it will overwrite `lib/api-types.ts`; this file is the interim
// contract and should be reconciled against the generated types at that point.
//
// Money crosses the boundary as numbers. `value_kind` / `result_kind` say which
// formatter from `lib/format.ts` applies, which is what keeps formatINR() the
// single formatter and stops pre-formatted money entering the API.

import type { Tone } from './tone';

export type ValueKind = 'money' | 'money_compact' | 'count' | 'pct' | 'ratio' | 'text';

/** ISO-8601 date, e.g. "2026-08-12". Pydantic `date` over the wire. */
export type IsoDate = string;

export interface StatCardView {
  label: string;
  value: number | string;
  value_kind: ValueKind;
  sub: string;
  tone: Tone;
}

export interface FlagRowView {
  item: string;
  desc: string;
  qty: number | null;
  unit: string | null;
  rate: number | null;
  amount: number | null;
  expected_qty: number | null;
  expected_unit: string | null;
  expected_amount: number | null;
  note: string;
  label: string;
  tone: Tone;
}

export interface FlagGroupView {
  name: string;
  items: FlagRowView[];
}

export interface QuestionView {
  number: number;
  text: string;
  status: string;
}

export interface PaymentStageView {
  label: string;
  pct: number;
  before_slab: boolean;
}

export interface BoqReviewView {
  loan_id: string;
  borrower: string;
  contractor: string | null;
  received_on: IsoDate | null;
  item_count: number;
  rev: number;
  cards: StatCardView[];
  groups: FlagGroupView[];
  all_groups: FlagGroupView[];
  questions: QuestionView[];
  payment_schedule: PaymentStageView[];
  /** The quoted contract total, straight from the API. */
  boq_total: number;
  pct_before_slab: number;
  amount_before_slab: number;
  gst_stated: boolean;
}

export interface SanctionBarView {
  label: string;
  value: number;
  pct_of_max: number;
  sub: string;
  tone: Tone;
}

export interface SanctionSectionView {
  name: string;
  quoted: number | null;
  quoted_note: string | null;
  market: number | null;
  delta: number;
  tone: Tone;
}

export interface SanctionOptionView {
  title: string;
  saves_label: string;
  desc: string;
}

export interface SanctionCheckView {
  loan_id: string;
  bars: SanctionBarView[];
  shortfall: number;
  sections: SanctionSectionView[];
  options: SanctionOptionView[];
}

export interface PortfolioRowView {
  loan_id: string;
  borrower: string;
  locality: string;
  paid_up_to: string;
  seen_on_site: string;
  behind_schedule: boolean;
  disbursed: number;
  exposure: number | null;
  gap: number | null;
  gap_note: string | null;
  action_label: string;
  tone: Tone;
  href: string;
}

export interface PortfolioView {
  cards: StatCardView[];
  rows: PortfolioRowView[];
}

export interface MathRowView {
  label: string;
  calc: string;
  result: number | string;
  result_kind: ValueKind;
  tone: Tone;
}

export interface StageView {
  name: string;
  sub: string;
  state: 'done' | 'current' | 'todo';
}

export interface EvidenceChipView {
  label: string;
  tone: Tone;
}

export interface PhotoView {
  slot_key: string;
  caption: string | null;
  chips: EvidenceChipView[];
}

export interface TrancheDecisionView {
  loan_id: string;
  borrower: string;
  locality: string;
  tranche_number: number;
  milestone: string;
  /** `paid` | `on_hold` | `upcoming`. Only `on_hold` is a draw awaiting a
   *  decision; the screen must not offer to release one already disbursed. */
  status: string;
  request_amount: number;
  recommendation: string;
  recommendation_tone: Tone;
  exposure: number | null;
  exposure_undefined: boolean;
  needs_human_review: boolean;
  confidence: string | null;
  stages: StageView[];
  math: MathRowView[];
  photos: PhotoView[];
  owner_view: string | null;
  officer_view: string | null;
  phases: PhaseHistoryView[];
}

export interface PhaseDecisionView {
  action: string;
  tone: Tone;
  decided_by: string;
  decided_at: string;
  note: string | null;
}

/** One build phase after the fact. Carried by both BuildProgressView and
 *  TrancheDecisionView, from one backend mapper, so the owner's account of the
 *  build and the lender's audit trail cannot tell different stories. */
export interface PhaseHistoryView {
  tranche_number: number;
  milestone: string;
  label: string;
  status: 'paid' | 'on_hold' | 'upcoming';
  status_label: string;
  tone: Tone;
  inspected_on: string | null;
  claimed_stage: string | null;
  observed_stage: string | null;
  /** False for phases released before Neev was verifying this loan. */
  observed_by_neev: boolean;
  photos: PhotoView[];
  evidence_notes: string[];
  confidence: string | null;
  needs_human_review: boolean;
  verified_value: number | null;
  /** Exposure AT that phase, not today's. */
  exposure: number | null;
  exposure_undefined: boolean;
  released_amount: number;
  disbursed_cum: number;
  recommendation: string | null;
  decision: PhaseDecisionView | null;
}

// ---------------------------------------------------------------------------
// Transcribed from src/backend/app/schemas/views.py. These were added
// backend-side in the routes task and never made it here, so screens needing
// them declared narrow local interfaces instead -- flagged twice by the screen
// agents. `npm run gen:types` regenerates this file from the OpenAPI schema;
// until that runs, this is the contract.
// ---------------------------------------------------------------------------

export interface LoanSummaryView {
  loan_id: string;
  borrower: string;
  locality: string;
  plot_label: string | null;
  built_up_sqft: number | null;
  sanctioned: number;
  disbursed: number;
  contractor: string | null;
  latest_rev: number | null;
  recommendation: string | null;
  exposure: number | null;
  gap: number | null;
  current_stage: string | null;
  tranche_count: number;
}

export interface ProgressTrancheView {
  number: number;
  name: string;
  sub: string;
  amount: number;
  status_label: string;
  tone: Tone;
  state: 'done' | 'current' | 'todo';
}

export interface StandingRowView {
  label: string;
  /** A string only ever carries the em dash for a figure nobody has verified. */
  value: number | string;
  value_kind: ValueKind;
  tone: Tone;
}

export interface BuildProgressView {
  loan_id: string;
  borrower: string;
  locality: string;
  plot_label: string | null;
  sanctioned: number;
  disbursed: number;
  current_stage: string | null;
  last_verified_on: string | null;
  paused: boolean;
  tranches: ProgressTrancheView[];
  standing: StandingRowView[];
  steps: string[];
  /** Negative when the sanction will not finish the house at local rates. */
  shortfall: number | null;
  phases: PhaseHistoryView[];
}

export interface ContractorRowView {
  id: string;
  name: string;
  meta: string;
  sites: number;
  flags_per_boq: number | null;
  underspecified_share: number | null;
  overrun_pct: number | null;
  sites_gone_quiet: number;
  tier: string;
  tone: Tone;
}

export interface ContractorScorecardView {
  rows: ContractorRowView[];
}
