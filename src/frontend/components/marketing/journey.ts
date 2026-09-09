// The four-stage journey strip. Copy taken verbatim from the `renderVals()` of
// `Neev Login.dc.html`, which is the only prototype that spells the stages out.
//
// It lives here rather than in either page because plan Task 14 puts the strip on
// Landing while the prototype draws it on Login: one list, two layouts. These are
// static marketing lines, not loan data — nothing here is a figure, so nothing
// here belongs in the API.

export interface JourneyStage {
  /** Stage number as the design shows it: "0" through "3", mono. */
  n: string;
  name: string;
  desc: string;
}

export const JOURNEY_STAGES: JourneyStage[] = [
  { n: '0', name: 'Before signing', desc: 'flags what’s inflated, missing or vague' },
  { n: '1', name: 'At sanction', desc: 'will the loan actually finish the house?' },
  { n: '2', name: 'Through the build', desc: 'photos verify each payment' },
  { n: '3', name: 'On every change', desc: 'extras priced against the signed contract' },
];

/** The same product from the other side of the table.
 *
 *  The borrower's four stages are a timeline of their build, and read as one:
 *  "before signing", "on every change" — things a borrower does. A credit
 *  officer signs nothing and orders no changes, so on `/login?role=bank` that
 *  list described somebody else's job, numbered from a stage 0 the officer
 *  never has. These are the four screens they actually work, in the order they
 *  work them: the book, then a loan's contract, then the draw in front of them,
 *  then whatever changed since.
 */
export const LENDER_STAGES: JourneyStage[] = [
  { n: '1', name: 'The book', desc: 'ranked by exposure, worst first' },
  { n: '2', name: 'The contract', desc: 'inflated, missing and vague items flagged' },
  { n: '3', name: 'Each disbursement', desc: 'site photographs against the milestone claimed' },
  { n: '4', name: 'Each change', desc: 'extras priced against what was signed' },
];
