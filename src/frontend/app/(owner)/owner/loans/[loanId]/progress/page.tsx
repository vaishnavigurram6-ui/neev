// Build Progress — Neev 3 Build Progress.dc.html.
//
// Scaffolded preview (plan Task 19), but the data here is real: the tranche
// ledger is `fixtures/draw_schedule.csv` with the seed's own tranche statuses,
// the standing figures are the pipeline fixture's risk assessment, and the
// last-verified evidence lines are the inspection notes the seed stores as photo
// captions. What is still a preview is the writing side — adding this month's
// photos needs `POST /api/loans/{id}/milestones` (Task 12).
//
// Where the mockup and the seeded case disagree, the seeded case wins: the
// mockup draws five tranche rows and shows the slab as paid, while the draw
// schedule for this loan has three and the seed holds the slab tranche pending
// the officer's decision — which is what the Tranche Decision screen acts on.
import Link from 'next/link';
import CalloutBanner from '@/components/owner/CalloutBanner';
import GuidanceList from '@/components/owner/GuidanceList';
import Panel from '@/components/owner/Panel';
import PreviewEmpty from '@/components/owner/PreviewEmpty';
import { formatDay, previewLoan, type PreviewTranche } from '@/components/owner/preview';
import Button from '@/components/ui/Button';
import CardTable, { type Column } from '@/components/ui/CardTable';
import Figure from '@/components/ui/Figure';
import KeyValueCard from '@/components/ui/KeyValueCard';
import PageHeader from '@/components/ui/PageHeader';
import PhotoSlot from '@/components/ui/PhotoSlot';
import StatusPill from '@/components/ui/StatusPill';
import StickyRail from '@/components/ui/StickyRail';
import { formatINR } from '@/lib/format';

const COPY = {
  eyebrow: 'THROUGH THE BUILD',
  title: 'Your build, payment by payment',
  pausedLead: "The next release is paused — and that's protecting you.",
  pausedBody:
    "More has been paid out than the structure is worth so far. Pausing now forces the re-scope while there's still money left to re-scope with.",
  pausedCta: 'See your options',
  paymentsTitle: 'Payments so far',
  photosTitle: "This month's site photos",
  photosCta: 'Report a milestone →',
  photosNote:
    'Take photos from the same spots each month — it speeds up verification and releases.',
  evidenceTitle: 'What your last verified set showed',
  standingTitle: 'Where you stand',
  paidLabel: 'Paid to your contractor',
  standingLabel: 'Work standing on site',
  leftLabel: 'Left in your sanction',
  neededLabel: 'Needed to finish',
  shortLead: "At today's rates you'd be ",
  shortTail: ' short of a finished house. Fixable now — much harder at the roof.',
  surplusLead: "At today's rates you'd have ",
  surplusTail: ' left over once the house is finished.',
  weekTitle: 'What to do this week',
  stepOne:
    'Send the 4 written questions from your contract review — they cover the over-priced RCC and the missing waterproofing.',
  stepTwo: 'Pick one of the three re-scope options and agree it with your contractor.',
  stepThree: 'Add this month’s photos so the next verification is instant.',
  questionsCta: 'questions',
  rescopeCta: 'Re-scope options',
  emptyWhat: 'This is where your payments, photos and site verifications would be listed.',
};

const TRANCHE_COLUMNS: Column<PreviewTranche>[] = [
  {
    key: 'milestone',
    header: 'Payment',
    render: (row) => (
      <div>
        <div className="text-[13.5px] font-semibold text-ink">{row.label}</div>
        <div className="mt-[2px] text-[12px] text-faint">{row.sub}</div>
      </div>
    ),
  },
  {
    key: 'amount',
    header: 'Amount',
    align: 'right',
    width: '140px',
    render: (row) => (
      <Figure
        value={formatINR(row.amount)}
        tone={row.status === 'on_hold' ? 'danger' : 'neutral'}
      />
    ),
  },
  {
    key: 'drawn',
    header: 'Drawn to date',
    align: 'right',
    width: '140px',
    render: (row) => <Figure value={formatINR(row.drawnToDate)} size="sm" />,
  },
  {
    key: 'status',
    header: 'Status',
    align: 'right',
    width: '130px',
    render: (row) => <StatusPill tone={row.tone} label={row.statusLabel} />,
  },
];

export default async function BuildProgressPage({
  params,
}: {
  params: Promise<{ loanId: string }>;
}) {
  const { loanId } = await params;
  const loan = previewLoan(loanId);

  const header = (
    <PageHeader
      eyebrow={COPY.eyebrow}
      title={COPY.title}
      sub={
        loan
          ? `${formatINR(loan.disbursed)} of ${formatINR(loan.sanctioned)} drawn${
              loan.currentMilestone ? ` · ${loan.currentMilestone.label.toLowerCase()} cast` : ''
            } · last verified ${formatDay(loan.lastVerifiedOn)}`
          : undefined
      }
      actions={<StatusPill tone="neutral" label="Preview" />}
    />
  );

  if (!loan) {
    return (
      <div className="flex flex-col gap-5">
        {header}
        <PreviewEmpty loanId={loanId} what={COPY.emptyWhat} />
      </div>
    );
  }

  const sanctionHref = `/owner/loans/${loanId}/sanction`;
  const undrawn = loan.sanctioned - loan.disbursed;
  const paused = loan.tranches.some((tranche) => tranche.status === 'on_hold');
  // `cost_to_complete_gap` is signed: negative is a shortfall, positive is room
  // to spare. The clean case must not be told it is short.
  const short = loan.costToCompleteGap < 0;

  return (
    <div className="flex flex-col gap-5">
      {header}

      {paused && (
        <CalloutBanner
          tone="warn"
          lead={COPY.pausedLead}
          body={COPY.pausedBody}
          action={
            <Button href={sanctionHref} variant="primary">
              {COPY.pausedCta}
            </Button>
          }
        />
      )}

      <div className="flex items-start gap-5">
        <div className="flex min-w-0 flex-1 flex-col gap-5">
          <div className="flex flex-col gap-[10px]">
            <h2 className="text-[14.5px] font-bold text-ink">{COPY.paymentsTitle}</h2>
            <CardTable
              columns={TRANCHE_COLUMNS}
              rows={loan.tranches}
              caption="Every tranche on this loan: the milestone it pays for, the amount, the cumulative total drawn after it, and whether it has been released."
              emptyMessage="No tranches have been scheduled on this loan yet."
            />
          </div>

          <Panel
            title={COPY.photosTitle}
            aside={
              <Link
                href={`/owner/loans/${loanId}/progress/report`}
                className="font-semibold text-action hover:underline"
              >
                {COPY.photosCta}
              </Link>
            }
            footer={COPY.photosNote}
          >
            <div className="grid grid-cols-3 gap-[10px]">
              {loan.photoSlots.map((slot) => (
                <PhotoSlot
                  key={slot.slotKey}
                  slotKey={slot.slotKey}
                  label={slot.label}
                  guidance={slot.guidance}
                />
              ))}
            </div>

            <div className="mt-[18px] border-t border-line pt-[14px]">
              <h3 className="text-[12.5px] font-semibold text-ink">
                {`${COPY.evidenceTitle} — ${formatDay(loan.lastVerifiedOn)}`}
              </h3>
              <div className="mt-[10px]">
                <GuidanceList marker="check" items={loan.lastVerifiedEvidence} />
              </div>
            </div>
          </Panel>
        </div>

        <StickyRail>
          <KeyValueCard
            title={COPY.standingTitle}
            rows={[
              {
                label: COPY.paidLabel,
                value: <Figure value={formatINR(loan.disbursed)} />,
              },
              {
                label: COPY.standingLabel,
                value: <Figure value={formatINR(loan.verifiedValue)} tone="danger" />,
              },
              {
                label: COPY.leftLabel,
                value: <Figure value={formatINR(undrawn)} />,
              },
              {
                label: COPY.neededLabel,
                value: <Figure value={formatINR(loan.costToComplete)} tone="danger" />,
              },
            ]}
            footer={
              <p className="text-[12.5px] leading-[1.6] text-sub">
                {short ? COPY.shortLead : COPY.surplusLead}
                <Figure
                  value={formatINR(Math.abs(loan.costToCompleteGap))}
                  tone={short ? 'danger' : 'success'}
                />
                {short ? COPY.shortTail : COPY.surplusTail}
              </p>
            }
          />

          <Panel title={COPY.weekTitle}>
            <GuidanceList
              marker="number"
              divided
              items={[COPY.stepOne, COPY.stepTwo, COPY.stepThree]}
            />
            <div className="mt-[14px] flex gap-2">
              <Button href={`/owner/loans/${loanId}/boq`} className="flex-1">
                {`Your ${loan.questions.length} ${COPY.questionsCta}`}
              </Button>
              <Button href={sanctionHref} variant="primary" className="flex-1">
                {COPY.rescopeCta}
              </Button>
            </div>
          </Panel>
        </StickyRail>
      </div>
    </div>
  );
}
