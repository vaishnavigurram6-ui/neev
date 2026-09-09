// Sign up — the same two-column split as Login, so arriving from the "Create
// one" link does not feel like leaving the product.
//
// Borrowers only. A credit officer's access to the whole book is provisioned,
// never self-served, which is why there is no role control on this page and no
// role field in the request. The left panel says so in one line rather than
// making a visitor find out by failing.
import type { Metadata } from 'next';
import Link from 'next/link';
import JourneyStages from '@/components/marketing/JourneyStages';
import { JOURNEY_STAGES } from '@/components/marketing/journey';
import AccessibilityCluster from '@/components/ui/AccessibilityCluster';
import Logo from '@/components/ui/Logo';
import SignupForm from './SignupForm';

export const metadata: Metadata = {
  title: 'Create an account',
  description: 'Open a Neev account and add the loan you are building against.',
  // Landing is the only indexable route in the product.
  robots: { index: false, follow: true },
};

export default function SignupPage() {
  return (
    <main className="grid min-h-screen grid-cols-[1fr_1.1fr]">
      <div className="flex flex-col border border-line bg-card px-[52px] py-12">
        <Link href="/" aria-label="Neev home">
          <Logo size={26} />
        </Link>

        <div className="my-auto py-10">
          <h1 className="text-[30px] font-bold leading-[1.3] tracking-[-0.02em] text-ink">
            Start with the
            <br />
            contract you signed.
          </h1>
          <p className="mt-[14px] max-w-[400px] text-[14px] leading-[1.7] text-faint">
            Add your loan and upload your Bill of Quantities. Neev reads it line
            by line and tells you what it finds.
          </p>
          <JourneyStages
            layout="rows"
            label="What Neev checks, stage by stage"
            stages={JOURNEY_STAGES}
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

        <div className="m-auto w-[400px] max-w-full py-8">
          <h2 className="text-[23px] font-bold tracking-[-0.02em] text-ink">
            Create your account
          </h2>
          <p className="mt-[6px] text-[13px] leading-[1.6] text-sub">
            For home builders. Lenders are set up by their bank.
          </p>

          <SignupForm />

          <p className="mt-[18px] text-center text-[13px] leading-[1.6] text-sub">
            Already have an account?{' '}
            <Link href="/login" className="font-semibold text-action underline decoration-1 underline-offset-2">
              Sign in
            </Link>
          </p>
        </div>

        <p className="text-center text-[11.5px] text-faint">
          English today · हिंदी, తెలుగు and read-aloud are coming
        </p>
      </div>
    </main>
  );
}
