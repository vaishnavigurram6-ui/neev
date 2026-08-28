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
