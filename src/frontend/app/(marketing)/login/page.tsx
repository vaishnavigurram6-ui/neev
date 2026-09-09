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
  // `?role=` used to preselect a side of the table, and no longer needs to: the
  // account decides the role, and the server answers with it. `next` still
  // matters — it is where the visitor was heading before the middleware turned
  // them away — and `actions.ts` refuses one outside the signed-in role's tree.

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
          <LoginForm next={next} />

          {/* The prototype sends this to Owner Onboarding, which is gated, so an
              unauthenticated click bounces off the middleware straight back here.
              It used to link to /login itself with onboarding as the destination —
              which navigates to the page you are already on, looks completely
              dead, and discards the number you had just typed. Logging in IS
              signing up here: no passwords, no separate registration. So this
              says that rather than linking anywhere. */}
          <p className="mt-[18px] text-center text-[13px] leading-[1.6] text-sub">
            New here? Just enter your number above — there is nothing to sign up for.
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
