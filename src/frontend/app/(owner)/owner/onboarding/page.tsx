// Owner Onboarding — ported from `design_handoff_neev/Neev 0 Owner Onboarding.dc.html`.
//
// Two things about the prototype do not survive contact with the route it lives
// on. Its header carries "Already have an account? Log in", and its stepper is
// the header — but `/owner/onboarding` sits inside the `(owner)` group behind the
// middleware, so everyone who reaches it is already signed in and gets the
// console's own TopBar from the layout. Offering them a log-in link would be
// copy that lies. The body copy is otherwise verbatim, including the headline's
// "400 houses": that is a marketing line, not a loan figure, and there is no
// endpoint that could or should serve it.
//
// The loan's own facts DO come from the API — `GET /api/loans/{id}` — because the
// wizard's later steps show the plot, the sanction and the contractor, and those
// are exactly the figures the no-literals rule is about.
import { notFound } from 'next/navigation';
import JourneyStages from '@/components/marketing/JourneyStages';
import { isLoanId, pickLoanFacts, type LoanFacts } from '@/components/owner/loan-facts';
import { ONBOARDING_STAGES } from '@/components/owner/onboarding-copy';
import ErrorState from '@/components/ui/ErrorState';
import { ApiError, apiGet } from '@/lib/api';
import { readSession } from '@/lib/session';
import OnboardingWizard from './OnboardingWizard';

const COPY = {
  headlineA: 'Your contractor has priced 400 houses.',
  headlineB: 'You’re pricing one.',
  standfirst:
    'Neev reads your construction contract, flags what’s inflated, missing or vague — then keeps checking it against real site progress until your house is finished.',
  stagesHeading: 'HOW NEEV STAYS WITH YOU',
  stagesLabel: 'How Neev stays with you, stage by stage',
  stagesNote:
    'One document, ingested once, used at every stage. Your lender sees the same evidence — fewer site-visit delays, faster releases.',
  errorTitle: 'We could not open your loan',
  errorBody:
    'Your details are safe. This is on our side — try again, and if it keeps happening your lender can re-send your link.',
};

export const metadata = { title: 'Check your contract — Neev' };

export default async function OwnerOnboardingPage() {
  const session = await readSession();
  // The layout has already redirected anyone without an owner session; this is
  // the type narrowing, not a second gate.
  // `session.loanId` is cookie data, and the cookie is an unsigned mock: it is
  // interpolated into a backend URL below, so it is validated first. See
  // `isLoanId` for what a forged one could otherwise reach.
  if (session === null || !isLoanId(session.loanId)) notFound();

  let loan: LoanFacts;
  try {
    loan = pickLoanFacts(await apiGet<LoanFacts>(`/api/loans/${session.loanId}`));
  } catch (cause) {
    if (cause instanceof ApiError && cause.status === 404) notFound();
    if (!(cause instanceof ApiError)) throw cause;
    // The wizard cannot run without the loan — step three shows its sanction
    // figures and the upload is addressed to its id — so the whole screen is the
    // error state, with a retry that simply reloads.
    return <ErrorState title={COPY.errorTitle} body={COPY.errorBody} retryHref="/owner/onboarding" />;
  }

  return (
    <div className="mx-auto w-full max-w-[960px]">
      <div className="mx-auto max-w-[620px] text-center">
        <h1 className="font-display text-[32px] font-bold leading-[1.25] tracking-[-0.02em] text-ink">
          {COPY.headlineA}
          <br />
          {COPY.headlineB}
        </h1>
        <p className="mt-3 text-[15px] leading-[1.6] text-sub">{COPY.standfirst}</p>
      </div>

      <OnboardingWizard loan={loan} />

      <section className="mx-auto mt-[52px] max-w-[720px]">
        <h2 className="text-center text-[12px] font-semibold uppercase tracking-[0.08em] text-faint">
          {COPY.stagesHeading}
        </h2>
        <JourneyStages
          layout="cards"
          label={COPY.stagesLabel}
          stages={ONBOARDING_STAGES}
          className="mt-[18px]"
        />
        <p className="mt-5 text-center text-[12.5px] leading-[1.6] text-faint">
          {COPY.stagesNote}
        </p>
      </section>
    </div>
  );
}
