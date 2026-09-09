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
import PhaseHistory from '@/components/loans/PhaseHistory';
import { ApiError, apiGet } from '@/lib/api';
import type { BuildProgressView } from '@/lib/types';
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
  onFile: 'On file —',
  reportedLead: 'Your photos are with your bank.',
  reportedBody:
    'They are filed against this milestone and the disbursement is queued for verification. Your officer sees the same frames you sent — no need to send them again.',
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
    header: 'Disbursed to date',
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
  searchParams,
}: {
  params: Promise<{ loanId: string }>;
  searchParams: Promise<{ reported?: string }>;
}) {
  const { loanId } = await params;
  // Set by Update Progress after a successful send. The owner has just handed
  // over the evidence for a payment; landing on an unchanged screen with no
  // acknowledgement is how someone ends up sending it twice.
  const justReported = (await searchParams).reported === '1';
  const loan = previewLoan(loanId);

  // The rest of this screen still runs on preview data (it is a scaffolded
  // screen), but the phase history is real: it comes from the same mapper the
  // lender's Tranche Decision reads, so the owner's account of their build and
  // the bank's audit trail cannot disagree. Fetched defensively -- a history
  // section is worth having, but not at the cost of the whole page.
  let phases: BuildProgressView['phases'] = [];
  let lastVerified: string | null = null;
  try {
    const progress = await apiGet<BuildProgressView>(`/api/loans/${loanId}/progress`);
    phases = progress.phases;
    lastVerified = progress.last_verified_on;
  } catch (cause) {
    if (!(cause instanceof ApiError)) throw cause;
  }

  // The frames already on file, newest phase first, for the slots below. They
  // come from the API rather than from a path in the bundle: a site photograph
  // is somebody's house being built, and `/api/loans/{id}/photos/{n}`
  // authorizes per loan where a file under public/ would be readable by anyone
  // who guessed its name.
  const onFile = [...phases]
    .reverse()
    .flatMap((phase) => phase.photos)
    .filter((photo) => photo.src);

  const reported = justReported ? (
    <CalloutBanner tone="success" lead={COPY.reportedLead} body={COPY.reportedBody} />
  ) : null;

  const header = (
    <PageHeader
      eyebrow={COPY.eyebrow}
      title={COPY.title}
      sub={
        loan
          ? `${formatINR(loan.disbursed)} of ${formatINR(loan.sanctioned)} disbursed${
              loan.currentMilestone ? ` · ${loan.currentMilestone.label.toLowerCase()} cast` : ''
            } · last verified ${formatDay(loan.lastVerifiedOn)}`
          : undefined
      }
      status={<StatusPill tone="neutral" label="Preview" />}
    />
  );

  if (!loan) {
    return (
      <div className="flex flex-col gap-5">
        {header}
        {reported}
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
      {reported}

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
              caption="Every tranche on this loan: the milestone it pays for, the amount, the cumulative total disbursed after it, and whether it has been released."
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
              {loan.photoSlots.map((slot, index) => (
                <PhotoSlot
                  key={slot.slotKey}
                  slotKey={slot.slotKey}
                  label={slot.label}
                  guidance={slot.guidance}
                  recorded={
                    onFile[index]?.src
                      ? {
                          src: onFile[index].src as string,
                          taken: lastVerified
                            ? `${COPY.onFile} ${formatDay(lastVerified)}`
                            : COPY.onFile,
                          alt: onFile[index].caption ?? slot.label,
                        }
                      : undefined
                  }
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

      <div className="mt-8">
        <PhaseHistory phases={phases} />
      </div>
    </div>
  );
}
