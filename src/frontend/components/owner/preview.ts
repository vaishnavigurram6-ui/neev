// Data for the scaffolded owner screens (plan Task 19).
//
// These five screens are routed and laid out but have no endpoint behind them
// yet: Tasks 12–13 give the backend its routes, and none of the view models
// these screens need — build progress, change orders, a revision diff — exists
// in `src/backend/app/schemas/views.py`. So rather than invent placeholder
// figures, every number and every row here is transcribed from what the seed
// already stores for the golden case:
//
//   fixtures/draw_schedule.csv                    -> the tranche ledger
//   src/backend/app/db/seed.py                    -> change orders, questions
//   src/backend/app/fixtures/loan_1001_pipeline.json
//                                                 -> risk figures, photo evidence
//
// The one exception is the revision-2 diff (`REV2`), which no fixture covers —
// it is the mockup's own list, and the screen says Preview.
//
// Shape note: this module is deliberately shaped like a view model, not like the
// screens. When `GET /api/loans/{id}/progress` and its siblings land, the pages
// swap `previewLoan()` for `apiGet()` and keep their markup.

import type { Tone } from '@/lib/tone';

/** "2026-08-10" -> "10 Aug 2026". UTC-pinned so the server and the client agree. */
const DAY = new Intl.DateTimeFormat('en-IN', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  timeZone: 'UTC',
});

export function formatDay(iso: string): string {
  return DAY.format(new Date(`${iso}T00:00:00Z`));
}

export type TrancheStatus = 'paid' | 'on_hold' | 'upcoming';

export interface PreviewTranche {
  number: number;
  /** Milestone as the owner screens name it. One vocabulary across all of them. */
  label: string;
  sub: string;
  amount: number;
  /** Cumulative drawn after this tranche — `disbursed_cum` in the draw schedule.
   *  Carried so the ledger ties out against the loan's `disbursed` headline
   *  instead of asking the reader to add the rows up. */
  drawnToDate: number;
  status: TrancheStatus;
  statusLabel: string;
  tone: Tone;
}

export interface PreviewMilestone {
  key: string;
  label: string;
  sub: string;
  state: 'done' | 'current' | 'todo';
}

export interface PreviewPhotoSlot {
  slotKey: string;
  label: string;
  guidance: string;
}

export interface PreviewQuestion {
  number: number;
  text: string;
  statusLabel: string;
  tone: Tone;
}

export type ChangeOrderState = 'pending' | 'accepted' | 'declined';

export interface PreviewChangeOrder {
  id: string;
  title: string;
  signedDesc: string;
  signedAmount: number;
  proposedDesc: string;
  proposedAmount: number;
  delta: number;
  neevsRead: string;
  statusLabel: string;
  /** Three states, not two: a declined change is settled but adds nothing to
   *  the contract, so `!pending` is never a safe stand-in for "accepted". */
  state: ChangeOrderState;
  tone: Tone;
}

export interface PreviewFix {
  was: string;
  title: string;
  detail: string;
  /** null when the fix moves no money; `deltaLabel` then carries the copy. */
  delta: number | null;
  deltaLabel: string | null;
  tone: Tone;
}

export interface PreviewRevision {
  rev: number;
  receivedOn: string;
  flagsResolved: number;
  fixes: PreviewFix[];
  quotedBefore: number;
  quotedBeforeWithExtras: number;
  total: number;
  coverPageDelta: number;
  savedAgainstExtras: number;
}

export interface PreviewLoan {
  loanId: string;
  borrower: string;
  plotLabel: string;
  locality: string;
  contractor: string;
  /** Signed BoQ total for the current revision. */
  boqTotal: number;
  rev: number;
  receivedOn: string;
  itemCount: number;
  flagCount: number;
  sanctioned: number;
  disbursed: number;
  verifiedValue: number;
  costToComplete: number;
  costToCompleteGap: number;
  lastVerifiedOn: string;
  tranches: PreviewTranche[];
  milestones: PreviewMilestone[];
  /** The milestone the owner would report next, or null on a fully drawn loan —
   *  there is then nothing to report, and the report screen says so rather than
   *  pre-checking a disabled radio. */
  currentMilestone: PreviewMilestone | null;
  /** What verifying that milestone releases. */
  nextRelease: number;
  /** Captions on the last verified photo set, from the pipeline's evidence notes. */
  lastVerifiedEvidence: string[];
  questions: PreviewQuestion[];
  changeOrders: PreviewChangeOrder[];
  /** Steel quantity on BoQ item 4.2 — the bill cross-check example. */
  steelQtyKg: number;
  /** The month's photo slots. One scheme, shared by both progress screens, so a
   *  photo uploaded from either lands in the same slot. */
  photoSlots: PreviewPhotoSlot[];
  revisions: PreviewRevision[];
}

// ---------------------------------------------------------------------------
// Loan 1001 — Ravi Kumar, Plot 47, Kompally. The golden case.
// ---------------------------------------------------------------------------

const MILESTONE_LABEL: Record<string, string> = {
  foundation: 'Foundation',
  plinth: 'Plinth',
  slab: 'Roof slab',
  brickwork_roof: 'Brickwork & roof',
  finishing: 'Finishing & handover',
};

/** The standard five-milestone plan. Loan 1001 draws against the first three. */
const MILESTONE_ORDER = ['foundation', 'plinth', 'slab', 'brickwork_roof', 'finishing'];

/** fixtures/draw_schedule.csv, rows for 1001, plus the seed's tranche statuses. */
const SCHEDULE_1001: {
  number: number;
  milestone: string;
  disbursedCum: number;
  inspectionDate: string;
  status: TrancheStatus;
}[] = [
  { number: 1, milestone: 'foundation', disbursedCum: 600000, inspectionDate: '2026-01-20', status: 'paid' },
  { number: 2, milestone: 'plinth', disbursedCum: 1200000, inspectionDate: '2026-03-05', status: 'paid' },
  { number: 3, milestone: 'slab', disbursedCum: 1800000, inspectionDate: '2026-08-10', status: 'on_hold' },
];

const STATUS_LABEL: Record<TrancheStatus, string> = {
  paid: 'Paid',
  on_hold: 'On hold',
  upcoming: 'Upcoming',
};

const STATUS_TONE: Record<TrancheStatus, Tone> = {
  paid: 'success',
  on_hold: 'danger',
  upcoming: 'neutral',
};

function trancheSub(status: TrancheStatus, inspectionDate: string): string {
  const day = formatDay(inspectionDate);
  if (status === 'paid') return `Verified & released ${day}`;
  if (status === 'on_hold') return `Verified from photos ${day} · paused pending re-scope`;
  return 'Final release';
}

function tranches1001(): PreviewTranche[] {
  let previousCum = 0;
  return SCHEDULE_1001.map((row) => {
    const amount = row.disbursedCum - previousCum;
    previousCum = row.disbursedCum;
    const label = MILESTONE_LABEL[row.milestone];
    return {
      number: row.number,
      label,
      sub: trancheSub(row.status, row.inspectionDate),
      amount,
      drawnToDate: row.disbursedCum,
      status: row.status,
      statusLabel: STATUS_LABEL[row.status],
      tone: STATUS_TONE[row.status],
    };
  });
}

function milestones1001(): PreviewMilestone[] {
  const drawn = new Map(SCHEDULE_1001.map((row) => [row.milestone, row]));
  // The milestone under review is the earliest scheduled one not yet released.
  const currentKey = SCHEDULE_1001.find((row) => row.status !== 'paid')?.milestone;
  const currentIndex = currentKey ? MILESTONE_ORDER.indexOf(currentKey) : -1;

  return MILESTONE_ORDER.map((key, index) => {
    const row = drawn.get(key);
    const state: PreviewMilestone['state'] =
      row?.status === 'paid' ? 'done' : index === currentIndex ? 'current' : 'todo';
    const sub =
      state === 'done' && row
        ? `released ${formatDay(row.inspectionDate)}`
        : state === 'current'
          ? 'you are here'
          : index === currentIndex + 1
            ? 'next'
            : '';
    return { key, label: MILESTONE_LABEL[key], sub, state };
  });
}

/** src/backend/app/db/seed.py — the four "Send before you sign" questions, all
 *  still `draft`, which is the state the seed actually stores. The mockup shows
 *  three replied and one awaiting; that is a later point in the same story. */
const QUESTION_STATUS: Record<string, { label: string; tone: Tone }> = {
  draft: { label: 'Not sent yet', tone: 'neutral' },
  sent: { label: 'Awaiting reply', tone: 'warn' },
  replied: { label: 'Replied', tone: 'success' },
};

const QUESTIONS_1001: { number: number; text: string; status: string }[] = [
  {
    number: 1,
    text: 'Confirm the TMT grade for item 4.2 — Fe 500 or Fe 500D per IS 1786 — in writing.',
    status: 'draft',
  },
  {
    number: 2,
    text: 'RCC M25 is priced at ₹9,800/cum against a ₹8,033 local benchmark. What is the basis?',
    status: 'draft',
  },
  {
    number: 3,
    text: 'External plaster and terrace waterproofing are absent. In scope, or extra — and at what rate?',
    status: 'draft',
  },
  {
    number: 4,
    text: '45% is due before slab. Please restructure toward the standard 25%-before-slab pattern.',
    status: 'draft',
  },
];

/** src/backend/app/db/seed.py `_seed_change_orders`. Both are still pending. */
const CHANGE_ORDERS_1001: {
  title: string;
  signedDesc: string;
  signedAmount: number;
  proposedDesc: string;
  proposedAmount: number;
  neevsRead: string;
  status: string;
  tone: Tone;
}[] = [
  {
    title: 'Kitchen platform upgrade',
    signedDesc: 'Granite for kitchen platform, 18mm — 6.5 sqm at ₹2,900',
    signedAmount: 18850,
    proposedDesc: 'Quartz composite platform, 20mm — 6.5 sqm at ₹5,400',
    proposedAmount: 35100,
    neevsRead:
      'Quartz at ₹5,400/sqm is within the Kompally range of ₹4,900–5,800, so the rate is fair. The change is a genuine upgrade, not a repricing of signed work.',
    status: 'pending',
    tone: 'warn',
  },
  {
    title: 'Additional electrical points',
    signedDesc: 'Concealed wiring per point — 68 points at ₹720',
    signedAmount: 48960,
    proposedDesc: 'Concealed wiring per point — 79 points at ₹860',
    proposedAmount: 67940,
    neevsRead:
      'The 11 extra points are reasonable. The rate rising from ₹720 to ₹860 on the same work is not — the signed rate should hold for the added points.',
    status: 'pending',
    tone: 'danger',
  },
];

const CHANGE_ORDER_STATUS: Record<ChangeOrderState, { label: string }> = {
  pending: { label: 'Awaiting your reply' },
  accepted: { label: 'Accepted' },
  declined: { label: 'Declined' },
};

function changeOrderState(status: string): ChangeOrderState {
  return status === 'accepted' || status === 'declined' ? status : 'pending';
}

/** Revision 2. The only block on any of these screens with no fixture behind
 *  it: the diff list, its deltas and its three totals are the mockup's own,
 *  verbatim.
 *
 *  Note the mockup does not reconcile with itself — its nine per-fix deltas sum
 *  to +₹1,76,000 while its rail states +₹1,60,000 on the cover page (and a
 *  ₹33,60,000 total against ₹32,00,000). Both figures are carried as authored:
 *  the plan's global constraints say numbers come from the mockups verbatim and
 *  are never recomputed or reconciled. Flagged for whoever owns the fixtures. */
const REV2: PreviewRevision = {
  rev: 2,
  receivedOn: '2026-08-19',
  flagsResolved: 9,
  quotedBefore: 3200000,
  quotedBeforeWithExtras: 3730000,
  total: 3360000,
  coverPageDelta: 160000,
  savedAgainstExtras: 370000,
  fixes: [
    {
      was: 'Rate +22%',
      title: 'RCC M25 re-priced to ₹8,200/cum',
      detail: 'Columns and roof slab (items 3.1–3.2) now within 2% of the Kompally benchmark.',
      delta: -54400,
      deltaLabel: null,
      tone: 'success',
    },
    {
      was: 'Rate +18%',
      title: 'Plinth beam re-priced to ₹8,300/cum',
      detail: 'M20 no longer billed at the M25 rate (item 2.3).',
      delta: -9750,
      deltaLabel: null,
      tone: 'success',
    },
    {
      was: 'No grade',
      title: 'TMT bars now "Fe 500 per IS 1786" @ ₹76/kg',
      detail: 'Grade in writing, at the honest market rate — the low-bid trap is closed.',
      delta: 67200,
      deltaLabel: null,
      tone: 'warn',
    },
    {
      was: 'Missing',
      title: 'External plaster added — 295 sqm @ ₹250',
      detail: '18mm double coat, now inside scope instead of a future extra.',
      delta: 73750,
      deltaLabel: null,
      tone: 'warn',
    },
    {
      was: 'Missing',
      title: 'Terrace waterproofing added — APP membrane @ ₹640',
      detail: '155 sqm incl. protection screed, per the benchmark rate.',
      delta: 99200,
      deltaLabel: null,
      tone: 'warn',
    },
    {
      was: 'Vague spec',
      title: 'Tiles: "Kajaria or Somany" named',
      detail:
        'Item 7.1 — brand and 600×600 spec in writing; substitution now needs your sign-off.',
      delta: null,
      deltaLabel: '—',
      tone: 'neutral',
    },
    {
      was: 'Vague spec',
      title: 'Wiring: Finolex FR copper · switches: Anchor Roma',
      detail: 'Items 9.1–9.2 — make and series named.',
      delta: null,
      deltaLabel: '—',
      tone: 'neutral',
    },
    {
      was: 'Front-loaded',
      title: 'Payment schedule restructured: 25% before slab',
      detail:
        'Advance 10% · foundation 10% · plinth 5% · slab 25% · brickwork & roof 30% · handover 20%.',
      delta: null,
      deltaLabel: '—',
      tone: 'neutral',
    },
    {
      was: 'GST silent',
      title: 'GST stated: 12% composite, included in rates',
      detail: 'No unbudgeted 12–18% at settlement.',
      delta: null,
      deltaLabel: 'stated',
      tone: 'success',
    },
  ],
};

/** The three shots a milestone needs, keyed the way the seed keys its photo
 *  rows: `{loanId}-{milestone}-{slot}`. Both progress screens read this, so the
 *  "wide shot from the gate" is one slot and not two. */
function photoSlots(loanId: string, milestoneKey: string): PreviewPhotoSlot[] {
  return [
    { slot: 'wide', label: 'Wide shot from the gate' },
    { slot: 'work', label: 'The new work, close up' },
    { slot: 'angle', label: 'Same angle as last month' },
  ].map((entry) => ({
    slotKey: `${loanId}-${milestoneKey}-${entry.slot}`,
    label: entry.label,
    guidance: 'Same spot every time — it is what makes the check instant.',
  }));
}

function loan1001(): PreviewLoan {
  const tranches = tranches1001();
  const milestones = milestones1001();
  const current = milestones.find((milestone) => milestone.state === 'current') ?? null;
  const currentTranche = tranches.find((tranche) => tranche.status !== 'paid');

  return {
    loanId: '1001',
    borrower: 'Ravi Kumar',
    plotLabel: 'Plot 47, Kompally',
    locality: 'Kompally',
    contractor: 'Sri Sai Constructions',
    boqTotal: 3200000,
    rev: 1,
    receivedOn: '2026-08-12',
    itemCount: 40,
    flagCount: 9,
    sanctioned: 2800000,
    disbursed: 1800000,
    verifiedValue: 1390000,
    costToComplete: 1580000,
    costToCompleteGap: -580000,
    lastVerifiedOn: '2026-08-10',
    tranches,
    milestones,
    currentMilestone: current,
    nextRelease: currentTranche?.amount ?? 0,
    lastVerifiedEvidence: [
      'Geotag matches Plot 47, Kompally.',
      'Timestamp 10 Aug, 11:42.',
      'Slab shuttering struck; surface finished. Consistent with the claimed stage.',
    ],
    questions: QUESTIONS_1001.map((question) => {
      const status = QUESTION_STATUS[question.status] ?? QUESTION_STATUS.draft;
      return {
        number: question.number,
        text: question.text,
        statusLabel: status.label,
        tone: status.tone,
      };
    }),
    changeOrders: CHANGE_ORDERS_1001.map((order, index) => {
      const state = changeOrderState(order.status);
      return {
        id: `CO-${index + 1}`,
        title: order.title,
        signedDesc: order.signedDesc,
        signedAmount: order.signedAmount,
        proposedDesc: order.proposedDesc,
        proposedAmount: order.proposedAmount,
        delta: order.proposedAmount - order.signedAmount,
        neevsRead: order.neevsRead,
        statusLabel: CHANGE_ORDER_STATUS[state].label,
        state,
        tone: order.tone,
      };
    }),
    steelQtyKg: 4800,
    photoSlots: photoSlots('1001', current?.key ?? 'unscheduled'),
    revisions: [REV2],
  };
}

/** The seed only carries this depth of detail for the golden case, so every
 *  other loan id gets `null` and the screens show their empty state rather than
 *  1001's figures under someone else's name. */
export function previewLoan(loanId: string): PreviewLoan | null {
  return loanId === '1001' ? loan1001() : null;
}

export function previewRevision(loan: PreviewLoan, rev: number): PreviewRevision | null {
  return loan.revisions.find((revision) => revision.rev === rev) ?? null;
}
