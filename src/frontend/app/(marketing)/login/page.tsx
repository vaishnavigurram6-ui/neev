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
import AccessibilityCluster from '@/components/ui/AccessibilityCluster';
import Logo from '@/components/ui/Logo';
import type { Role } from '@/lib/session';
import LoginForm from './LoginForm';

export const metadata: Metadata = {
  title: 'Log in',
  description: 'Log in to Neev with your mobile number. No passwords.',
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
  // `?role=` wins where a lender-facing link sets it. Otherwise the destination
  // says which side of the table this is: the middleware and the (bank) layout
  // both send officers here as `?next=/bank/...` with no role, and a lender who
  // does not notice the toggle would otherwise be signed in as an owner and have
  // their own destination discarded as out-of-tree.
  const asked = first(params.role);
  const role: Role =
    asked === 'bank' || (asked !== 'owner' && next.startsWith('/bank')) ? 'bank' : 'owner';

  return (
    <main className="grid min-h-screen grid-cols-[1fr_1.1fr]">
      <div className="flex flex-col border border-line bg-card px-[52px] py-12">
        <Link href="/" aria-label="Neev home">
          <Logo size={26} />
        </Link>

        <div className="my-auto py-10">
          <h1 className="text-[30px] font-bold leading-[1.3] tracking-[-0.02em] text-ink">
            The home builder’s side
            <br />
            of the table.
          </h1>
          <p className="mt-[14px] max-w-[400px] text-[14px] leading-[1.7] text-faint">
            Your contract read line by line. Your money released against real progress. Your changes
            priced against what you signed.
          </p>
          <JourneyStages
            layout="rows"
            label="What Neev checks, stage by stage"
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
          <LoginForm initialRole={role} next={next} />

          {/* The prototype sends this to Owner Onboarding, which is gated: an
              unauthenticated click would bounce off the middleware straight back
              to this page. Logging in *is* signing up here — there are no
              passwords and no separate registration — so the link sets onboarding
              as where this login lands instead of pretending to leave. */}
          <p className="mt-[18px] text-center text-[13px] text-sub">
            New here?{' '}
            <Link
              href="/login?role=owner&next=%2Fowner%2Fonboarding"
              className="font-semibold text-action hover:underline"
            >
              Start by uploading your contract
            </Link>
          </p>
        </div>

        <p className="text-center text-[11.5px] text-faint">
          Works in English, हिंदी and తెలుగు · every screen can be read aloud
        </p>
      </div>
    </main>
  );
}
