// Neev Login — ported from `design_handoff_neev/Neev Login.dc.html`.
//
// The two-column split, the copy and the type scale are the prototype's. The
// interactive half is <LoginForm>; everything on this page is static, so it stays
// a server component and the client bundle carries only the form.
//
// `?next=` arrives from the middleware when it turns away a request with no
// session, and `?role=` lets a lender-facing link preselect the right side of the
// toggle. Both are read here rather than with useSearchParams so the form needs
// no Suspense boundary and renders selected on first paint.
import type { Metadata } from 'next';
import Link from 'next/link';
import JourneyStages from '@/components/marketing/JourneyStages';
import { JOURNEY_STAGES, LENDER_STAGES } from '@/components/marketing/journey';
import SegmentedToggle from '@/components/ui/SegmentedToggle';
import AccessibilityCluster from '@/components/ui/AccessibilityCluster';
import Logo from '@/components/ui/Logo';
import LoginForm from './LoginForm';

/** Which side of the table this page is talking to. Copy only: the credential
 *  decides what the visitor can actually see. */
const OWNER_PANEL = {
  headlineTop: 'The home builder’s side',
  headlineBottom: 'of the table.',
  standfirst:
    'Your contract read line by line. Your money released against real progress. Your changes priced against what you signed.',
  stagesLabel: 'What Neev checks, stage by stage',
  stages: JOURNEY_STAGES,
};

const LENDER_PANEL = {
  // "Draw" is what construction lending calls it, but it is jargon on the
  // first screen a lender ever sees. "Disbursement" is the word the data model
  // already uses (`disbursed`, `disbursed_cum`), and unlike "payment" it cannot
  // be misread as the borrower's repayment, which is money moving the other
  // way. The rest of the product's copy was swept to match; `draw_schedule`
  // survives as a form field name and a fixture filename, neither of which a
  // visitor reads.
  headlineTop: 'Every disbursement, against',
  headlineBottom: 'what is actually built.',
  standfirst: 'The whole book ranked by exposure, and the evidence behind every release, on one screen.',
  stagesLabel: 'What a credit officer works through in Neev',
  stages: LENDER_STAGES,
};

export const metadata: Metadata = {
  title: 'Log in',
  description: 'Log in to Neev with your username and password.',
  // Landing is the only indexable route in the product.
  robots: { index: false, follow: true },
};

function first(value: string | string[] | undefined): string {
  if (Array.isArray(value)) return value[0] ?? '';
  return value ?? '';
}

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  const next = first(params.next);
  // `?role=` no longer preselects anything, because there is nothing to
  // preselect: the account decides the role and the server answers with it.
  // The old toggle let the CALLER declare its own role — any ten digits plus
  // role=bank opened the whole book — which is an authorization hole wearing a
  // label, not a control.
  //
  // It still decides which side of the table this PAGE talks to, and that
  // distinction is the point: wayfinding is not authorization. A lender who
  // follows "For lenders" from the marketing header should not arrive at a
  // headline reading "The home builder's side of the table" and wonder whether
  // they are in the wrong place. Nothing here affects what the credential can
  // do — `actions.ts` still refuses a `next` outside the role the server
  // actually granted.
  const asked = first(params.role);
  const forLender = asked === 'bank' || (asked !== 'owner' && next.startsWith('/bank'));
  const panel = forLender ? LENDER_PANEL : OWNER_PANEL;

  return (
    <main className="grid min-h-screen grid-cols-[1fr_1.1fr]">
      <div className="flex flex-col border border-line bg-card px-[52px] py-12">
        <Link href="/" aria-label="Neev home">
          <Logo size={26} />
        </Link>

        <div className="my-auto py-10">
          <h1 className="text-[30px] font-bold leading-[1.3] tracking-[-0.02em] text-ink">
            {panel.headlineTop}
            <br />
            {panel.headlineBottom}
          </h1>
          <p className="mt-[14px] max-w-[400px] text-[14px] leading-[1.7] text-faint">
            {panel.standfirst}
          </p>
          <JourneyStages
            layout="rows"
            label={panel.stagesLabel}
            stages={panel.stages}
            className="mt-8 max-w-[400px]"
          />
        </div>

        <p className="text-[11.5px] text-sub">
          नींव — the foundation. The first thing built, the first thing verified.
        </p>
      </div>

      <div className="flex flex-col px-7 py-6">
        <div className="flex justify-end">
          <AccessibilityCluster />
        </div>

        <div className="m-auto w-[400px] max-w-full">
          {/* Wayfinding, not authorization. This only decides which side of the
              table the page talks to -- the copy on the left, and the wording
              here -- and `?role=` is the same thing a "For lenders" link in the
              marketing header already carries. What the visitor can actually
              see is decided by the credential: the backend answers with the
              role the account holds and `actions.ts` refuses a `next` outside
              it. The old control was a different thing wearing the same shape,
              a form field the SERVER believed, so any ten digits plus
              `role=bank` opened the whole book. Reading it from the URL is what
              keeps it a label. */}
          <div className="flex items-center justify-between gap-3">
            <h2 className="text-[23px] font-bold tracking-[-0.02em] text-ink">Welcome back</h2>
            <SegmentedToggle
              options={[
                { value: 'owner', label: 'Home builder' },
                { value: 'bank', label: 'Lender' },
              ]}
              value={forLender ? 'bank' : 'owner'}
              paramName="role"
              skin={forLender ? 'bank' : 'owner'}
              label="Which side of the table you are on"
            />
          </div>

          <LoginForm next={next} />

          <p className="mt-[18px] text-center text-[13px] leading-[1.6] text-sub">
            New here?{' '}
            <Link
              href="/signup"
              className="font-semibold text-action underline decoration-1 underline-offset-2"
            >
              Create an account
            </Link>
          </p>

        </div>

        {/* The prototype's line promises Hindi, Telugu and read-aloud. Neither
            translation nor text-to-speech is built (spec §10), and the
            accessibility cluster renders both as "coming soon" -- so stating it
            as fact here contradicts the product two clicks away. */}
        <p className="text-center text-[11.5px] text-faint">
          English today · हिंदी, తెలుగు and read-aloud are coming
        </p>
      </div>
    </main>
  );
}
