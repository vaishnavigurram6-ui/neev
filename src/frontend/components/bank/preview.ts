// Data for the scaffolded bank screens (plan Task 19).
//
// The contractor rows are the three the seed stores — `CONTRACTORS` in
// `src/backend/app/db/seed.py` — not the four in the mockup, which name
// different firms with different figures. The seed's are the ones the loans in
// the book actually point at, so they win: Sri Sai Constructions is loan 1001's
// contractor on the BoQ Review header, and a scorecard that named a firm no loan
// references would be a screen with nothing behind it.
//
// `GET /api/contractors` (Task 13) returns `ContractorScorecardView`; when it
// lands, this module is replaced by the call and the screen keeps its markup.

import type { Tone } from '@/lib/tone';

export interface ContractorRow {
  id: string;
  name: string;
  /** Loans on the book with this contractor. */
  sites: number;
  flagsPerBoq: number;
  underspecifiedShare: number;
  overrunPct: number;
  sitesGoneQuiet: number;
  tier: string;
  tone: Tone;
  /** Per-metric tone, so a bad column reads as bad without a colour prop on any
   *  component. The mockup hand-colours these four numbers per contractor; the
   *  bands below reproduce that pattern from the figures themselves. */
  metricTones: {
    flags: Tone;
    underspecified: Tone;
    overrun: Tone;
    quiet: Tone;
  };
}

/** Above `danger`, it is a warn; above `warn`, a success. One band per metric. */
function band(value: number, danger: number, warn: number): Tone {
  if (value >= danger) return 'danger';
  if (value >= warn) return 'warn';
  return 'success';
}

/** Tiers are a status, so they take a tone from the one vocabulary. */
const TIER_TONE: Record<string, Tone> = {
  WATCH: 'danger',
  REVIEW: 'warn',
  RELIABLE: 'success',
};

const CONTRACTORS: Omit<ContractorRow, 'tone' | 'metricTones'>[] = [
  {
    id: 'c1',
    name: 'Sri Sai Constructions',
    sites: 4,
    flagsPerBoq: 7.2,
    underspecifiedShare: 0.31,
    overrunPct: 0.18,
    sitesGoneQuiet: 1,
    tier: 'WATCH',
  },
  {
    id: 'c2',
    name: 'Bhavya Builders',
    sites: 3,
    flagsPerBoq: 3.1,
    underspecifiedShare: 0.14,
    overrunPct: 0.07,
    sitesGoneQuiet: 0,
    tier: 'REVIEW',
  },
  {
    id: 'c3',
    name: 'Sree Rama Constructions',
    sites: 3,
    flagsPerBoq: 1.4,
    underspecifiedShare: 0.05,
    overrunPct: 0.02,
    sitesGoneQuiet: 0,
    tier: 'RELIABLE',
  },
];

/** Worst first, the way the portfolio hotlist ranks its rows. */
export function contractorScorecard(): ContractorRow[] {
  return [...CONTRACTORS]
    .map((row) => ({
      ...row,
      tone: TIER_TONE[row.tier] ?? 'neutral',
      metricTones: {
        flags: band(row.flagsPerBoq, 5, 2),
        underspecified: band(row.underspecifiedShare, 0.25, 0.1),
        overrun: band(row.overrunPct, 0.15, 0.05),
        quiet: band(row.sitesGoneQuiet, 1, 1),
      },
    }))
    .sort((a, b) => b.flagsPerBoq - a.flagsPerBoq);
}

/** Bank Onboarding. The loan count is the seeded book; the three thresholds are
 *  the ones the pipeline actually applies — the 1.00 exposure hold threshold and
 *  the 25%-before-slab rule both appear verbatim in the fixture's own reasoning,
 *  and confidence below MEDIUM is what routes a tranche to a physical visit. */
export const SETUP = {
  loanCount: 10,
  exposureHold: 1,
  pctBeforeSlab: 0.25,
  confidenceFloor: 'MEDIUM',
  confidenceOptions: ['LOW', 'MEDIUM', 'HIGH'],
  /** The borrower invite link, one per loan. Shown for the golden case. */
  inviteLoanId: '1001',
  invitePrefix: 'neev.in/j/HDFC-',
} as const;
