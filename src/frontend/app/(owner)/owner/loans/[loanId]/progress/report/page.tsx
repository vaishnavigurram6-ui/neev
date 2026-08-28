// Update Progress — Neev 3b Update Progress.dc.html.
//
// Scaffolded preview (plan Task 19). The four steps are one real <form> with
// real labelled controls: the mockup's milestone tiles are radio inputs, its
// image slots are the kit's `PhotoSlot`, its bills strip is a multi-file
// `Dropzone`, and its "anything to add" panel is a labelled <textarea>. Sending
// needs `POST /api/loans/{id}/milestones` (Task 12), so the submit button is
// disabled and says why rather than pretending to send.
//
// The mockup is written for the foundation milestone — "Footings done?", a
// ₹2,80,000 release — which is not where this loan is: the seed has foundation
// and plinth released and the slab tranche pending. So the milestone-specific
// copy is templated from the loan's own current milestone and the release figure
// comes from the draw schedule.
import CalloutBanner from '@/components/owner/CalloutBanner';
import GuidanceList from '@/components/owner/GuidanceList';
import Panel from '@/components/owner/Panel';
import PreviewEmpty from '@/components/owner/PreviewEmpty';
import { previewLoan } from '@/components/owner/preview';
import Button from '@/components/ui/Button';
import Dropzone from '@/components/ui/Dropzone';
import Figure from '@/components/ui/Figure';
import PageHeader from '@/components/ui/PageHeader';
import PhotoSlot from '@/components/ui/PhotoSlot';
import StatusPill from '@/components/ui/StatusPill';
import StickyRail from '@/components/ui/StickyRail';
import { formatINR, formatQty } from '@/lib/format';

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
  submitWhy:
    'Sending a milestone for verification needs the milestone endpoint, which is not wired up on this preview screen yet.',
  submitLead: 'This screen is a preview.',
  submitBody:
    'The form is real and the figures are your own, but nothing is sent until the verification endpoint is connected.',
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
      status={<StatusPill tone="neutral" label="Preview" />}
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
        <form className="flex min-w-0 flex-1 flex-col gap-5">
          <Panel title={COPY.stepOneTitle}>
            <fieldset>
              <legend className="sr-only">{COPY.stepOneLegend}</legend>
              <div className="grid grid-cols-5 gap-2">
                {loan.milestones.map((option) => (
                  <label
                    key={option.key}
                    className={`flex items-start gap-2 rounded-card border px-3 py-[12px] ${
                      option.state === 'current'
                        ? 'border-action bg-success-tint'
                        : 'border-line bg-card'
                    } ${option.state === 'done' ? 'opacity-70' : 'cursor-pointer'}`}
                  >
                    <input
                      type="radio"
                      name="milestone"
                      value={option.key}
                      defaultChecked={option.state === 'current'}
                      disabled={option.state === 'done'}
                      className="mt-[3px] flex-none accent-action"
                    />
                    <span className="min-w-0">
                      <span className="block text-[12px] font-semibold text-ink">
                        {option.label}
                      </span>
                      <span className="mt-[2px] block text-[10.5px] leading-[1.4] text-faint">
                        {option.sub}
                      </span>
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>
          </Panel>

          <Panel
            title={COPY.stepTwoTitle}
            aside={`${loan.photoSlots.length}${COPY.stepTwoAsideTail}`}
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
            <div className="mt-[14px] flex flex-wrap gap-[6px]">
              <StatusPill tone="neutral" label={COPY.checkLocation} />
              <StatusPill tone="neutral" label={COPY.checkTimestamp} />
              <StatusPill tone="neutral" label={COPY.checkAngle} />
            </div>
          </Panel>

          <Panel
            title={`${COPY.stepThreeTitle} — ${COPY.stepThreeOptional}`}
            aside={COPY.stepThreeAside}
            footer={
              <p>
                {COPY.billsNoteLead}
                <Figure value={`${formatQty(loan.steelQtyKg)} kg`} size="sm" />
                {COPY.billsNoteTail}
              </p>
            }
          >
            <Dropzone
              name="bills"
              accept="application/pdf,image/*"
              label={COPY.billsLabel}
              hint={COPY.billsHint}
              multiple
            />
          </Panel>

          <Panel title={`${COPY.stepFourTitle} — ${COPY.stepFourOptional}`}>
            <label htmlFor="milestone-notes" className="sr-only">
              {COPY.notesLabel}
            </label>
            <textarea
              id="milestone-notes"
              name="notes"
              rows={3}
              placeholder={COPY.notesPlaceholder}
              className="w-full rounded-[10px] border border-input-border bg-bg px-4 py-3 text-[13px] text-ink placeholder:text-faint"
            />
            <div className="mt-[16px] flex items-center justify-end gap-3">
              {/* The reason a control is inert has to be readable without a
                  mouse: a disabled button is out of the tab order and `title`
                  alone reaches nobody using a keyboard or a screen reader. */}
              <p id="submit-why" className="text-[11.5px] text-faint">
                {COPY.submitWhy}
              </p>
              <Button
                type="submit"
                variant="primary"
                disabled
                reason={COPY.submitWhy}
              >
                {COPY.submit}
              </Button>
            </div>
          </Panel>

          <CalloutBanner tone="neutral" lead={COPY.submitLead} body={COPY.submitBody} />
        </form>

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
