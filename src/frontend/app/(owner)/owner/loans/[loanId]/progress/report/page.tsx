// Update Progress — Neev 3b Update Progress.dc.html.
//
// The four steps are one real <form> with real labelled controls: the mockup's
// milestone tiles are radio inputs, its image slots are the kit's `PhotoSlot`,
// its bills strip is a multi-file `Dropzone`, and its "anything to add" panel
// is a labelled <textarea>. It sends: `ReportForm` collects the downscaled
// photographs and POSTs them to `/api/loans/{id}/milestones`, which files them
// against the tranche they are evidence for and flips it to needs-review — so
// the lender sees the frames on their own loan page and tranche card.
//
// The form itself is a client component because the photographs live in it;
// the header, the rail and the loan's figures stay on the server.
//
// The mockup is written for the foundation milestone — "Footings done?", a
// ₹2,80,000 release — which is not where this loan is: the seed has foundation
// and plinth released and the slab tranche pending. So the milestone-specific
// copy is templated from the loan's own current milestone and the release figure
// comes from the draw schedule.
import GuidanceList from '@/components/owner/GuidanceList';
import Panel from '@/components/owner/Panel';
import PreviewEmpty from '@/components/owner/PreviewEmpty';
import { previewLoan } from '@/components/owner/preview';
import Button from '@/components/ui/Button';
import Figure from '@/components/ui/Figure';
import PageHeader from '@/components/ui/PageHeader';
import StickyRail from '@/components/ui/StickyRail';
import { formatINR } from '@/lib/format';
import ReportForm from './ReportForm';

const COPY = {
  eyebrow: 'BUILD PROGRESS · REPORT A MILESTONE',
  titleTail: ' done? Show us.',
  subLead: 'Your photos are the evidence that releases the ',
  subTail: ' payment — verified in minutes, not after a site-visit queue.',
  back: 'Back to build progress',
  stepOneTitle: '1 · Which milestone is complete?',
  stepOneLegend: 'Which milestone is complete?',
  stepTwoTitle: "2 · Add today's photos",
  stepTwoAsideTail: ' needed · same spots as last time',
  checkLocation: 'Location check runs on submit',
  checkTimestamp: 'Timestamp check runs on submit',
  checkAngle: 'Same-angle check runs on submit',
  stepThreeTitle: '3 · Attach bills',
  stepThreeOptional: 'optional, but speeds up release',
  stepThreeAside: 'photo or PDF',
  billsLabel: 'Cement, steel, labour and contractor bills',
  billsHint: 'Photo or PDF. Add as many as you have.',
  billsNoteLead: 'Bills are cross-checked against your BoQ quantities — ',
  billsNoteTail:
    ' of steel billed should match the steel your slab needs. They go to the bank with the photos as the disbursement record.',
  stepFourTitle: '4 · Anything to add?',
  stepFourOptional: 'optional',
  notesLabel: 'Anything to add?',
  notesPlaceholder: 'e.g. "Anti-termite treatment done before PCC, bill attached"',
  submit: 'Send for verification',
  sending: 'Sending your photos…',
  needPhoto: 'Add at least one photo — the photos are the evidence.',
  failed: 'Your report was not sent. Try again in a moment.',
  refused: 'This loan is not the one you are signed in for.',
  signIn: 'Your session has expired. Sign in again and send it once more.',
  unconfirmed:
    'The upload did not complete, so nothing was recorded. Check your connection and send it again.',
  billsNotSent:
    'Bills are held here for now — verification reads the photos, so bills are not part of what is sent yet.',
  submitLead: 'What your bank receives.',
  submitBody:
    'Your photos and note go straight into the loan file against this milestone, and the disbursement is marked for verification. Your officer sees the same frames you sent.',
  onSubmitTitle: 'What happens on submit',
  onSubmitOne:
    'Photos are read against your BoQ — footings, PCC and starter bars checked as line items, not a vague "15%".',
  onSubmitTwo: "Value in place is computed from your contract's own rates.",
  onSubmitThree:
    'Your bank gets the evidence with a release recommendation — usually same day.',
  releasesLabel: 'Releases on verification',
  goodTitle: 'Good photos = fast release',
  goodOne: 'Stand at the gate for the wide shot — same spot every time.',
  goodTwo: 'Get the whole trench and the steel in frame, in daylight.',
  goodThree: 'Blurry or mismatched photos route to a physical visit — nothing is auto-rejected.',
  emptyWhat: 'This is where you would report a finished milestone with today’s photos.',
};

export default async function UpdateProgressPage({
  params,
}: {
  params: Promise<{ loanId: string }>;
}) {
  const { loanId } = await params;
  const loan = previewLoan(loanId);
  const milestone = loan?.currentMilestone;

  const header = (
    <PageHeader
      eyebrow={COPY.eyebrow}
      title={milestone ? `${milestone.label}${COPY.titleTail}` : 'Report a milestone'}
      sub={
        milestone
          ? `${COPY.subLead}${milestone.label.toLowerCase()}${COPY.subTail}`
          : undefined
      }
      actions={
        <>
          <Button href={`/owner/loans/${loanId}/progress`}>{COPY.back}</Button>
        </>
      }
    />
  );

  if (!loan || !milestone) {
    return (
      <div className="flex flex-col gap-5">
        {header}
        <PreviewEmpty loanId={loanId} what={COPY.emptyWhat} />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      {header}

      <div className="flex items-start gap-5">
        <ReportForm
          loanId={loanId}
          milestones={loan.milestones}
          slots={loan.photoSlots}
          currentKey={milestone.key}
          steelQtyKg={loan.steelQtyKg}
          copy={COPY}
        />

        <StickyRail>
          <Panel
            title={COPY.onSubmitTitle}
            footer={
              <div className="flex items-baseline justify-between gap-3">
                <span className="text-[12.5px] text-sub">{COPY.releasesLabel}</span>
                <Figure value={formatINR(loan.nextRelease)} tone="success" size="lg" />
              </div>
            }
          >
            <GuidanceList
              marker="number"
              items={[COPY.onSubmitOne, COPY.onSubmitTwo, COPY.onSubmitThree]}
            />
          </Panel>

          <Panel title={COPY.goodTitle}>
            <GuidanceList items={[COPY.goodOne, COPY.goodTwo, COPY.goodThree]} />
          </Panel>
        </StickyRail>
      </div>
    </div>
  );
}
