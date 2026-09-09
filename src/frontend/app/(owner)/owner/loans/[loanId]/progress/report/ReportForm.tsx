'use client';

// The four steps of reporting a milestone, as one form that actually sends.
//
// Client-side because the photographs live here: `PhotoSlot` downscales each
// pick to 1600px and hands back a File, and those Files have to be collected
// into one multipart body. `POST /api/loans/{id}/milestones` (the relay next
// door) is the only writer.
//
// What is sent is what the endpoint accepts: the stage, one to six photographs,
// and the note. Bills are collected by the form but not yet part of the
// verification record — step 3 says so rather than implying they travel.
import { useRouter } from 'next/navigation';
import { useRef, useState } from 'react';
import CalloutBanner from '@/components/owner/CalloutBanner';
import Panel from '@/components/owner/Panel';
import type { PreviewMilestone, PreviewPhotoSlot } from '@/components/owner/preview';
import Button from '@/components/ui/Button';
import Dropzone from '@/components/ui/Dropzone';
import Figure from '@/components/ui/Figure';
import PhotoSlot from '@/components/ui/PhotoSlot';
import StatusPill from '@/components/ui/StatusPill';
import { formatQty } from '@/lib/format';

export interface ReportCopy {
  stepOneTitle: string;
  stepOneLegend: string;
  stepTwoTitle: string;
  stepTwoAsideTail: string;
  checkLocation: string;
  checkTimestamp: string;
  checkAngle: string;
  stepThreeTitle: string;
  stepThreeOptional: string;
  stepThreeAside: string;
  billsLabel: string;
  billsHint: string;
  billsNoteLead: string;
  billsNoteTail: string;
  billsNotSent: string;
  stepFourTitle: string;
  stepFourOptional: string;
  notesLabel: string;
  notesPlaceholder: string;
  submit: string;
  sending: string;
  needPhoto: string;
  failed: string;
  refused: string;
  signIn: string;
  unconfirmed: string;
  submitLead: string;
  submitBody: string;
}

/** At least one photograph, at most six — the endpoint's own range. Asking for
 *  three and accepting one is deliberate: a borrower with one usable frame is
 *  better served by a verification that runs than by a form that refuses. */
const MAX_PHOTOS = 6;

export default function ReportForm({
  loanId,
  milestones,
  slots,
  currentKey,
  steelQtyKg,
  copy,
}: {
  loanId: string;
  milestones: PreviewMilestone[];
  slots: PreviewPhotoSlot[];
  currentKey: string;
  steelQtyKg: number;
  copy: ReportCopy;
}) {
  const router = useRouter();
  // Keyed by slot, so re-picking the same slot replaces rather than appends.
  const [photos, setPhotos] = useState<Record<string, File>>({});
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  // A second POST is a second set of evidence on the same tranche. The button
  // is disabled while sending, but a keyboard Enter can land between the fetch
  // starting and React re-rendering; this closes that window.
  const inFlight = useRef(false);

  const chosen = Object.values(photos).slice(0, MAX_PHOTOS);

  const submit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (inFlight.current) return;

    if (chosen.length === 0) {
      setError(copy.needPhoto);
      return;
    }

    const form = event.currentTarget;
    const fields = new FormData(form);
    const body = new FormData();
    const stage = fields.get('milestone');
    if (typeof stage === 'string' && stage) body.set('stage', stage);
    const note = fields.get('notes');
    if (typeof note === 'string' && note.trim()) body.set('note', note.trim());
    for (const file of chosen) body.append('photos', file);

    inFlight.current = true;
    setPending(true);
    setError(null);

    let failure = copy.failed;
    try {
      const response = await fetch(`/api/loans/${loanId}/milestones`, {
        method: 'POST',
        body,
      });
      if (response.ok) {
        // Reporting a milestone starts an inspection: the same two agents a BoQ
        // analysis uses read the photographs and re-price the draw. When one
        // starts, follow it on the Analyzing screen — a borrower who has asked
        // for a payment should watch the check that decides it, not land on an
        // unchanged page. `job_id` is null when there is no stored analysis to
        // price against, and then Build Progress is the honest destination.
        const payload: unknown = await response.json().catch(() => null);
        const job =
          typeof payload === 'object' && payload !== null && 'job_id' in payload
            ? (payload as { job_id: unknown }).job_id
            : null;
        if (typeof job === 'string' && job) {
          router.push(
            `/owner/loans/${loanId}/analyzing?job=${encodeURIComponent(job)}&kind=milestone`
          );
          return;
        }
        router.push(`/owner/loans/${loanId}/progress?reported=1`);
        // `pending` stays set deliberately — the navigation is the completion,
        // and re-enabling the button under a leaving page invites a resend.
        return;
      }
      if (response.status === 401) {
        failure = copy.signIn;
      } else if (response.status === 403) {
        failure = copy.refused;
      } else if (response.status < 500) {
        const payload: unknown = await response.json().catch(() => null);
        const detail =
          typeof payload === 'object' && payload !== null && 'detail' in payload
            ? (payload as { detail: unknown }).detail
            : undefined;
        if (typeof detail === 'string' && detail) failure = detail;
      }
    } catch {
      // A refused connection or an aborted upload. Nothing was recorded, and
      // the generic message already says so.
      failure = copy.unconfirmed;
    }

    setError(failure);
    inFlight.current = false;
    setPending(false);
  };

  return (
    <form onSubmit={submit} className="flex min-w-0 flex-1 flex-col gap-5">
      <Panel title={copy.stepOneTitle}>
        <fieldset>
          <legend className="sr-only">{copy.stepOneLegend}</legend>
          <div className="grid grid-cols-5 gap-2">
            {milestones.map((option) => (
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
                  defaultChecked={option.key === currentKey}
                  disabled={option.state === 'done'}
                  className="mt-[3px] flex-none accent-action"
                />
                <span className="min-w-0">
                  <span className="block text-[12px] font-semibold text-ink">{option.label}</span>
                  <span className="mt-[2px] block text-[10.5px] leading-[1.4] text-faint">
                    {option.sub}
                  </span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>
      </Panel>

      <Panel title={copy.stepTwoTitle} aside={`${slots.length}${copy.stepTwoAsideTail}`}>
        <div className="grid grid-cols-3 gap-[10px]">
          {slots.map((slot) => (
            <PhotoSlot
              key={slot.slotKey}
              slotKey={slot.slotKey}
              label={slot.label}
              guidance={slot.guidance}
              onFile={(file) => setPhotos((held) => ({ ...held, [slot.slotKey]: file }))}
            />
          ))}
        </div>
        <div className="mt-[14px] flex flex-wrap gap-[6px]">
          <StatusPill tone="neutral" label={copy.checkLocation} />
          <StatusPill tone="neutral" label={copy.checkTimestamp} />
          <StatusPill tone="neutral" label={copy.checkAngle} />
        </div>
      </Panel>

      <Panel
        title={`${copy.stepThreeTitle} — ${copy.stepThreeOptional}`}
        aside={copy.stepThreeAside}
        footer={
          <p>
            {copy.billsNoteLead}
            <Figure value={`${formatQty(steelQtyKg)} kg`} size="sm" />
            {copy.billsNoteTail}
          </p>
        }
      >
        <Dropzone
          name="bills"
          accept="application/pdf,image/*"
          label={copy.billsLabel}
          hint={copy.billsHint}
          multiple
        />
        {/* Said out loud rather than implied: the verification endpoint takes
            photographs, so bills chosen here do not travel with them yet. */}
        <p className="mt-[8px] text-[11.5px] leading-[1.5] text-faint">{copy.billsNotSent}</p>
      </Panel>

      <Panel title={`${copy.stepFourTitle} — ${copy.stepFourOptional}`}>
        <label htmlFor="milestone-notes" className="sr-only">
          {copy.notesLabel}
        </label>
        <textarea
          id="milestone-notes"
          name="notes"
          rows={3}
          placeholder={copy.notesPlaceholder}
          className="w-full rounded-[10px] border border-input-border bg-bg px-4 py-3 text-[13px] text-ink placeholder:text-faint"
        />
        <div className="mt-[16px] flex items-center justify-end gap-3">
          <p
            id="report-status"
            aria-live="polite"
            className={`text-[11.5px] leading-[1.5] ${error ? 'text-danger' : 'text-faint'}`}
          >
            {pending ? copy.sending : (error ?? `${chosen.length} of ${slots.length} photos chosen`)}
          </p>
          <Button
            type="submit"
            variant="primary"
            disabled={pending}
            aria-describedby="report-status"
          >
            {pending ? copy.sending : copy.submit}
          </Button>
        </div>
      </Panel>

      <CalloutBanner tone="neutral" lead={copy.submitLead} body={copy.submitBody} />
    </form>
  );
}
