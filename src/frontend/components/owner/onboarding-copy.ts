// Onboarding's own wording for the four-stage strip, verbatim from the
// `renderVals()` of `Neev 0 Owner Onboarding.dc.html`.
//
// It is a second copy set rather than a replacement for `JOURNEY_STAGES`: Login
// and Landing say the same four things in half a line each, and Onboarding — the
// screen where somebody is deciding whether to hand over their contract — says
// them at length. Same stages, same order, different room to say it in.
//
// Nothing here is a figure, so nothing here belongs in the API.

import type { JourneyStage } from '@/components/marketing/journey';

export const ONBOARDING_STAGES: JourneyStage[] = [
  {
    n: '0',
    name: 'Before signing',
    desc: 'Inflated rates, missing scope and vague specs flagged — as questions to send your contractor.',
  },
  {
    n: '1',
    name: 'At sanction',
    desc: 'Will the approved amount actually finish the house at local rates? Know before drawdown.',
  },
  {
    n: '2',
    name: 'Through the build',
    desc: 'Site photos checked against your contract at every payment — stalls caught early.',
  },
  {
    n: '3',
    name: 'On every change',
    desc: 'Each change order priced against what you signed, so extras stay honest.',
  },
];
