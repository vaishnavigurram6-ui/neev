// Analyzing — ported from `design_handoff_neev/Neev 0b Analyzing.dc.html`.
//
// A thin server shell over one client component. The shell exists so the loan's
// own facts (the contractor whose BoQ this is, the locality whose rates it is
// being checked against, and whether a finished report already exists to skip
// ahead to) are fetched on the server like every other screen's data, and so the
// "no job to watch" case never mounts an EventSource at all.
//
// The job id is a query parameter, which is the URL-state rule: a reload keeps
// watching the same run, and the registry replays every event it already
// emitted. That is also why there is no separate "resume" path — resuming and
// starting are the same subscription.
import { notFound } from 'next/navigation';
import AnalyzingLive from '@/components/owner/AnalyzingLive';
import { isLoanId, pickLoanFacts, type LoanFacts } from '@/components/owner/loan-facts';
import Button from '@/components/ui/Button';
import EmptyState from '@/components/ui/EmptyState';
import { ApiError, apiGet } from '@/lib/api';

const COPY = {
  noJobTitle: 'There is no check running',
  noJobBody:
    'This page follows a contract check while it runs. Upload your Bill of Quantities and it will open here.',
  noJobCta: 'Upload your BoQ',
  reportCta: 'See your last report',
};

export const metadata = { title: 'Reading your contract — Neev' };

export default async function AnalyzingPage({
  params,
  searchParams,
}: {
  params: Promise<{ loanId: string }>;
  searchParams: Promise<{ job?: string | string[] }>;
}) {
  const { loanId } = await params;
  // The route segment is client input, and `proxy.ts` only checks it against the
  // (forgeable) session cookie — so validate it before it reaches a backend URL.
  if (!isLoanId(loanId)) notFound();
  const { job } = await searchParams;
  const jobId = typeof job === 'string' && job.length > 0 ? job : null;

  let loan: LoanFacts | null = null;
  try {
    loan = pickLoanFacts(await apiGet<LoanFacts>(`/api/loans/${loanId}`));
  } catch (cause) {
    if (cause instanceof ApiError && cause.status === 404) notFound();
    // Any other failure — the backend down, a timeout — is not fatal here. The
    // stream is what this screen is for, and it is relayed by a route handler
    // that does not depend on this call. Losing the loan record costs the header
    // its contractor and locality, and nothing else.
    if (!(cause instanceof ApiError)) throw cause;
  }

  if (jobId === null) {
    // Landing here with no job to watch: a bookmark, a back button, or a link
    // shared after the run finished. There is no "latest job for this loan"
    // endpoint to fall back to — jobs live in an in-process registry keyed by
    // id — so the honest answer is to say so and offer both real destinations.
    return (
      <EmptyState
        title={COPY.noJobTitle}
        body={COPY.noJobBody}
        action={
          <div className="flex gap-[10px]">
            <Button href="/owner/onboarding" variant="primary">
              {COPY.noJobCta}
            </Button>
            {loan !== null && loan.latest_rev !== null && (
              <Button href={`/owner/loans/${loanId}/boq`} variant="outline">
                {COPY.reportCta}
              </Button>
            )}
          </div>
        }
      />
    );
  }

  return <AnalyzingLive jobId={jobId} loanId={loanId} loan={loan} />;
}
