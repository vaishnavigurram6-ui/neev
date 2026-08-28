// Upload Revision — Neev 1a Upload Revision.dc.html.
//
// Scaffolded preview (plan Task 19): real chrome, real layout, real seeded
// figures for the golden case, and a visible Preview pill because the re-check
// itself needs the upload pipeline from Task 15 and the `POST /api/loans/{id}/boq`
// route from Task 12.
//
// Copy is the mockup's, verbatim. Every figure comes from `previewLoan()`; none
// is written into this file.
import Link from 'next/link';
import GuidanceList from '@/components/owner/GuidanceList';
import Panel from '@/components/owner/Panel';
import PreviewEmpty from '@/components/owner/PreviewEmpty';
import { formatDay, previewLoan, type PreviewQuestion } from '@/components/owner/preview';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import CardTable, { type Column } from '@/components/ui/CardTable';
import Dropzone from '@/components/ui/Dropzone';
import PageHeader from '@/components/ui/PageHeader';
import StatusPill from '@/components/ui/StatusPill';
import StickyRail from '@/components/ui/StickyRail';

const COPY = {
  eyebrow: 'MY CONTRACT · REVISION',
  title: 'Got the revised contract? Upload it here.',
  sub: 'We re-check every line against the benchmarks — not just the flagged ones — and show you exactly what changed.',
  dropLabel: 'Drop the revised BoQ',
  dropHint: 'PDF, Excel or photos — same as before. Takes about a minute to re-check.',
  submit: 'Re-check this revision',
  submitWhy:
    'Re-checking a revision runs the BoQ pipeline, which is not wired up on this preview screen yet.',
  next: 'what happens next →',
  questionsNote: 'Replies received in writing are attached to your case file automatically.',
  whyTitle: 'Why re-check everything',
  whyBody:
    'A revision sometimes fixes the flagged lines and quietly raises others. Neev diffs the whole document, so nothing moves without you seeing it.',
  waitTitle: 'While you wait for the revision',
  waitOne: "Don't sign or pay an advance until the revision clears the check.",
  waitTwo: "Nudge on the payment schedule — it's the one still unanswered.",
  waitThreeLead: 'Preview the ',
  waitThreeLink: 'sanction check',
  waitThreeTail: ' so you know your number going in.',
  emptyWhat: 'This is where you would upload your contractor’s revised contract.',
};

const QUESTION_COLUMNS: Column<PreviewQuestion>[] = [
  {
    key: 'text',
    header: 'Question',
    render: (row) => <span className="text-[13px] leading-[1.5] text-sub">{row.text}</span>,
  },
  {
    key: 'status',
    header: 'Status',
    align: 'right',
    width: '150px',
    render: (row) => <StatusPill tone={row.tone} label={row.statusLabel} />,
  },
];

export default async function UploadRevisionPage({
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
      sub={COPY.sub}
      actions={
        <>
          <StatusPill tone="neutral" label="Preview" />
          <Button href={`/owner/loans/${loanId}/boq`}>Back to my contract</Button>
        </>
      }
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

  const comparingAgainst = `Comparing against: Rev ${loan.rev}, received ${formatDay(
    loan.receivedOn
  )} · ${loan.flagCount} flags`;

  return (
    <div className="flex flex-col gap-5">
      {header}

      <div className="flex items-start gap-5">
        <div className="flex min-w-0 flex-1 flex-col gap-5">
          <Card className="p-[22px]">
            <form className="flex flex-col gap-[14px]">
              <Dropzone
                name="revised_boq"
                accept="application/pdf,.xlsx,.xls,image/*"
                label={COPY.dropLabel}
                hint={COPY.dropHint}
              />
              <div className="flex items-center justify-between gap-4">
                <span className="text-[12.5px] text-faint">{comparingAgainst}</span>
                <Link
                  href={`/owner/loans/${loanId}/analyzing`}
                  className="text-[12.5px] font-semibold text-action hover:underline"
                >
                  {COPY.next}
                </Link>
              </div>
              <div className="flex items-center justify-end gap-3">
                {/* A disabled button is out of the tab order and its `title` is
                    not reliably announced, so the reason is visible text too. */}
                <p id="recheck-why" className="text-[11.5px] text-faint">
                  {COPY.submitWhy}
                </p>
                <Button
                  type="submit"
                  variant="primary"
                  disabled
                  title={COPY.submitWhy}
                  aria-describedby="recheck-why"
                >
                  {COPY.submit}
                </Button>
              </div>
            </form>
          </Card>

          <div className="flex flex-col gap-[10px]">
            <h2 className="text-[14.5px] font-bold text-ink">
              {`Your ${loan.questions.length} questions — where they stand`}
            </h2>
            <CardTable
              columns={QUESTION_COLUMNS}
              rows={loan.questions}
              caption="The questions to send your contractor before signing, and where each one stands."
              emptyMessage="No questions have been drafted for this contract yet."
            />
            <p className="text-[12px] leading-[1.5] text-faint">{COPY.questionsNote}</p>
          </div>
        </div>

        <StickyRail>
          <Panel title={COPY.whyTitle}>
            <p className="text-[13px] leading-[1.65] text-sub">{COPY.whyBody}</p>
          </Panel>
          <Panel title={COPY.waitTitle}>
            <GuidanceList
              items={[
                COPY.waitOne,
                COPY.waitTwo,
                <span key="sanction">
                  {COPY.waitThreeLead}
                  <Link
                    href={`/owner/loans/${loanId}/sanction`}
                    className="font-semibold text-action hover:underline"
                  >
                    {COPY.waitThreeLink}
                  </Link>
                  {COPY.waitThreeTail}
                </span>,
              ]}
            />
          </Panel>
        </StickyRail>
      </div>
    </div>
  );
}
