// One borrower's file, for the officer who holds the loan.
//
// The book drilled straight from a portfolio row into a single tranche
// decision, which meant an officer could act on a draw without ever seeing the
// build it belonged to: no borrower, no contractor, no site photographs, no
// history. This is the level in between — the loan, its money, its evidence and
// its draws — and the decision cards are reached from here.
//
// Composed from endpoints that already exist rather than a new screen-shaped
// one: `GET /api/loans/{id}` for the loan's own facts, `/progress` for the
// ladder and the phase record (which carries the photographs the borrower
// sent), and `/boq/latest` for what the contract check found. All three are
// loan-scoped and readable by a lender; none is bank-specific, which is why
// nothing here needed a new mapper.
import PhaseHistory from '@/components/loans/PhaseHistory';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import CardTable, { type Column } from '@/components/ui/CardTable';
import EmptyState from '@/components/ui/EmptyState';
import Figure from '@/components/ui/Figure';
import PageHeader from '@/components/ui/PageHeader';
import StatCard from '@/components/ui/StatCard';
import StatusPill from '@/components/ui/StatusPill';
import { formatByKind } from '@/components/bank/kindFormat';
import { ApiError, apiGet } from '@/lib/api';
import { formatINR, formatRatio } from '@/lib/format';
import type { BoqReviewView, BuildProgressView, LoanSummaryView, ProgressTrancheView } from '@/lib/types';

const COPY = {
  eyebrow: 'Loan file',
  back: '← Back to the book',
  ladderTitle: 'Disbursement schedule',
  ladderCaption:
    'Every disbursement on this loan: the milestone it is tied to, what it releases, and where it stands.',
  decide: 'Open decision',
  contractTitle: 'What the contract check found',
  contractSub: 'From the borrower s latest BoQ revision.',
  noContract: 'No BoQ has been analysed for this loan yet.',
  noContractBody:
    'The borrower has not uploaded a bill of quantities, so there is no line-by-line check to read. The disbursement schedule below is still authoritative.',
  notFound: 'No such loan on the book',
  notFoundBody: 'Check the loan number, or go back to the portfolio and pick it from there.',
  evidenceNote:
    'Photographs are the borrower s own, sent from Update Progress. They open full size in a new tab.',
  stageUnknown: 'not reported',
};

/** A draw the officer can still act on. `state` is the ladder's own vocabulary:
 *  `done` is disbursed, `current` is the one under review, `todo` is ahead of
 *  the build. The API supplies the label and the tone, so neither is
 *  re-derived here. */
function awaitingDecision(tranche: ProgressTrancheView): boolean {
  return tranche.state === 'current';
}

function ladderColumns(): Column<ProgressTrancheView>[] {
  return [
    {
      key: 'number',
      header: 'Tranche',
      width: '70px',
      render: (row) => <Figure value={`T${row.number}`} size="sm" skin="bank" />,
    },
    {
      key: 'milestone',
      header: 'Milestone',
      // The row's drill-in. A button in every row read as five calls to action
      // where there is only ever one — and "Open decision" did not fit the
      // column it was in. The draw an officer actually has to answer is the
      // primary button in the page header; from here the milestone opens any
      // draw, decided or not.
      render: (row) => (
        <div>
          <span className="text-[13px] font-semibold text-action underline decoration-1 underline-offset-2">
            {row.name}
          </span>
          <p className="mt-[2px] text-[11.5px] text-faint">{row.sub}</p>
          <span className="sr-only">{` — open disbursement ${row.number}`}</span>
        </div>
      ),
    },
    {
      key: 'amount',
      header: 'Releases',
      align: 'right',
      width: '130px',
      render: (row) => <Figure value={formatINR(row.amount)} skin="bank" />,
    },
    {
      key: 'status',
      header: 'Standing',
      align: 'right',
      width: '120px',
      render: (row) => (
        <StatusPill skin="bank" tone={row.tone} label={row.status_label} size="sm" />
      ),
    },
  ];
}

export default async function LenderLoanFilePage({
  params,
}: {
  params: Promise<{ loanId: string }>;
}) {
  const { loanId } = await params;

  let loan: LoanSummaryView;
  try {
    loan = await apiGet<LoanSummaryView>(`/api/loans/${loanId}`);
  } catch (cause) {
    if (cause instanceof ApiError && cause.status === 404) {
      return (
        <div className="flex flex-col gap-5">
          <PageHeader
            eyebrow={COPY.eyebrow}
            title={COPY.notFound}
            actions={
              <Button skin="bank" href="/bank/portfolio">
                {COPY.back}
              </Button>
            }
          />
          <EmptyState skin="bank" title={COPY.notFound} body={COPY.notFoundBody} />
        </div>
      );
    }
    throw cause;
  }

  // A loan can be on the book with no BoQ and no draw schedule yet. Neither is
  // an error, and neither should take the page down with it.
  const progress = await apiGet<BuildProgressView>(`/api/loans/${loanId}/progress`).catch(
    (cause: unknown) => {
      if (cause instanceof ApiError && cause.status === 404) return null;
      throw cause;
    }
  );
  const boq = await apiGet<BoqReviewView>(`/api/loans/${loanId}/boq/latest`).catch(
    (cause: unknown) => {
      if (cause instanceof ApiError && cause.status === 404) return null;
      throw cause;
    }
  );

  const undrawn = loan.sanctioned - loan.disbursed;
  const pending = progress?.tranches.find(awaitingDecision);

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        eyebrow={COPY.eyebrow}
        title={loan.borrower}
        sub={[loan.plot_label, loan.locality, loan.contractor]
          .filter(Boolean)
          .join(' · ')}
        status={
          loan.recommendation ? (
            <StatusPill
              skin="bank"
              tone={loan.recommendation === 'RELEASE' ? 'success' : 'danger'}
              label={loan.recommendation}
            />
          ) : undefined
        }
        actions={
          <div className="flex items-center gap-2">
            {pending && (
              <Button
                skin="bank"
                variant="primary"
                href={`/bank/loans/${loanId}/tranches/${pending.number}`}
              >
                {COPY.decide} · T{pending.number}
              </Button>
            )}
            <Button skin="bank" href="/bank/portfolio">
              {COPY.back}
            </Button>
          </div>
        }
      />

      <div className="grid grid-cols-4 gap-[10px]">
        <StatCard
          skin="bank"
          label="SANCTIONED"
          value={formatINR(loan.sanctioned)}
          sub={`${loan.tranche_count} disbursements · ${loan.built_up_sqft ?? '—'} sqft`}
        />
        <StatCard
          skin="bank"
          label="DISBURSED"
          value={formatINR(loan.disbursed)}
          sub={`${formatINR(undrawn)} still undisbursed`}
          tone={loan.disbursed > 0 ? 'neutral' : 'success'}
        />
        <StatCard
          skin="bank"
          label="EXPOSURE"
          value={loan.exposure === null ? '—' : formatRatio(loan.exposure)}
          sub={
            loan.exposure === null
              ? 'no verified value yet'
              : 'disbursed ÷ verified value in place'
          }
          tone={loan.exposure !== null && loan.exposure > 1 ? 'danger' : 'success'}
        />
        <StatCard
          skin="bank"
          label="STAGE ON SITE"
          value={progress?.current_stage ?? COPY.stageUnknown}
          sub={
            progress?.last_verified_on
              ? `last verified ${progress.last_verified_on}`
              : 'never verified'
          }
          tone={progress?.paused ? 'danger' : 'neutral'}
        />
      </div>

      {boq ? (
        <Card skin="bank" className="p-[20px]">
          <div className="flex flex-wrap items-baseline justify-between gap-3">
            <div>
              <h2 className="text-[14.5px] font-bold text-ink">{COPY.contractTitle}</h2>
              <p className="mt-1 text-[12.5px] text-sub">
                {COPY.contractSub} Revision {boq.rev}, {boq.item_count} lines.
              </p>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-4 gap-[10px]">
            {boq.cards.map((card) => (
              <StatCard
                key={card.label}
                skin="bank"
                label={card.label}
                value={formatByKind(card.value, card.value_kind)}
                sub={card.sub}
                tone={card.tone}
              />
            ))}
          </div>
        </Card>
      ) : (
        <EmptyState skin="bank" title={COPY.noContract} body={COPY.noContractBody} />
      )}

      {progress && progress.tranches.length > 0 && (
        <Card skin="bank" className="p-[20px]">
          <h2 className="text-[14.5px] font-bold text-ink">{COPY.ladderTitle}</h2>
          <div className="mt-3">
            <CardTable
              skin="bank"
              columns={ladderColumns()}
              rows={progress.tranches}
              rowHref={(row) => `/bank/loans/${loanId}/tranches/${row.number}`}
              rowHrefColumn="milestone"
              caption={COPY.ladderCaption}
            />
          </div>
        </Card>
      )}

      {progress && progress.phases.length > 0 && (
        <Card skin="bank" className="p-[20px]">
          <PhaseHistory phases={progress.phases} skin="bank" />
          <p className="mt-3 text-[11.5px] leading-[1.5] text-faint">{COPY.evidenceNote}</p>
        </Card>
      )}
    </div>
  );
}
