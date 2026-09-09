'use client';

// The three-step wizard from `Neev 0 Owner Onboarding.dc.html`: Upload → Plot →
// Loan. The prototype draws the stepper and step one; steps two and three exist
// only as two unlit pills, so their contents are decided here.
//
// WHAT THEY CONTAIN, AND WHY SO LITTLE. `POST /api/loans/{id}/boq` takes exactly
// two things: the file, and `built_up_sqft`. The plot, the locality, the
// sanctioned amount and the contractor are already on the loan — the bank put
// them there, which is how the owner came to have a link to this screen at all.
// So step two collects the one figure the endpoint accepts and shows the plot
// facts it belongs to, and step three confirms the sanction figures rather than
// pretending to write them. Inventing fields with no endpoint behind them would
// look like more product and be less.
//
// One <form> per step, per the plan. The file therefore has to survive a step
// change, which is why the chosen File is lifted into state here rather than
// left in the input: the Dropzone unmounts when step two mounts.
//
// The upload goes to `/api/loans/[loanId]/boq` on this origin — a route handler,
// not a server action. See that file for why: a server action's request body is
// capped at 1 MB and this body is a scanned contract.
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useId, useRef, useState } from 'react';
import type { LoanFacts } from '@/components/owner/loan-facts';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import Dropzone, { dropzoneInputId } from '@/components/ui/Dropzone';
import { formatINR, formatQty } from '@/lib/format';

const COPY = {
  steps: ['Upload your BoQ', 'Your plot & area', 'Your loan'],

  // Step 1 — verbatim from the prototype.
  dropLabel: 'Drop your Bill of Quantities here',
  dropHint: 'PDF, JPEG, PNG or WebP — up to 10 MB. Demo mode replays a sample, not your upload.',
  volumeNote: 'Typically 80–150 line items · read in about a minute',
  sampleLead: 'no BoQ yet? ',
  sampleLink: 'see a sample report',
  held: 'Using ',
  heldTail: ' — choose another file to replace it.',
  noFile: 'Choose a PDF or a JPEG, PNG or WebP image of your BoQ.',
  tooBig: 'That file is larger than we can read in one go. Split it, or send the pages as photos.',
  wrongKind: 'Upload a PDF, JPEG, PNG or WebP. Export spreadsheets to PDF first.',

  // Step 2.
  plotTitle: 'Your plot & area',
  plotLead:
    'Your lender has already given us the plot. Check the built-up area — every rate we compare against is per square foot, so this is the one figure worth getting right.',
  plotLabel: 'Plot',
  localityLabel: 'Where you are building',
  areaLabel: 'Built-up area',
  areaUnit: 'sq ft',
  areaHint: 'All floors added up. Your contractor’s BoQ usually states it on the first page.',
  areaMissing: 'Enter the built-up area in square feet.',
  areaNotANumber: 'Enter the built-up area as digits only.',
  areaImplausible: 'That does not look like a built-up area in square feet. Check the figure.',

  // Step 3.
  loanTitle: 'Your loan',
  loanLead:
    'These are the figures your lender holds. We check whether they finish the house at local rates — so if anything here is wrong, tell your lender before we start.',
  sanctionedLabel: 'Sanctioned',
  drawnLabel: 'Released so far',
  contractorLabel: 'Your contractor',
  contractorUnknown: 'Not on file yet',
  confirmLabel: 'These match my sanction letter.',
  confirmMissing: 'Confirm the figures match your sanction letter before we start.',

  back: 'Back',
  next: 'Continue',
  start: 'Start the check',
  starting: 'Reading your contract…',
  failed: 'We could not start the check just now. Please try again in a moment.',
  tooLarge: 'The service would not accept a file that size. Try splitting it.',
  refused: 'We could not start the check: ',
};

/** The golden demo case — the one loan the authored fixtures cover, and so the
 *  only BoQ Review that can stand in as a sample. The prototype's link is
 *  `href="#"`; spec §7.4 says point it at the real thing. */
export const GOLDEN_CASE_LOAN_ID = '1001';

import { ACCEPT, MAX_UPLOAD_BYTES, looksReadable } from '@/components/owner/upload-validation';
const FILE_FIELD = 'file';

/** Well past any real BoQ, and matched to the upload relay's 180s timeout: 20 MB
 *  inside that window is about 0.9 Mbps sustained, which a domestic Indian uplink
 *  can hold. A cap the timeout cannot honour would reject slow uploads with an
 *  outage message and invite an identical retry. */

/** A built-up area outside this range is a typo, not a house. */
const MIN_SQFT = 100;
const MAX_SQFT = 100_000;


type Step = 0 | 1 | 2;

/** Which control a message belongs to. `form` is for a failure that belongs to
 *  no field — a refused or unreachable upload. */
type Scope = 'file' | 'area' | 'confirm' | 'form';

interface FieldError {
  scope: Scope;
  message: string;
}

export default function OnboardingWizard({ loan }: { loan: LoanFacts }) {
  const router = useRouter();
  const ids = useId();

  const [step, setStep] = useState<Step>(0);
  const [file, setFile] = useState<File | null>(null);
  const [sqft, setSqft] = useState(loan.built_up_sqft === null ? '' : String(loan.built_up_sqft));
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState<FieldError | null>(null);
  const [pending, setPending] = useState(false);

  // The submit button is disabled while pending, but a keyboard Enter can land
  // between the fetch starting and React re-rendering. This closes that window,
  // because a second POST is a second analysis job.
  const inFlight = useRef(false);

  const fileErrorId = `${ids}-file-error`;
  const areaId = `${ids}-area`;
  const areaHintId = `${ids}-area-hint`;
  const areaErrorId = `${ids}-area-error`;
  const confirmErrorId = `${ids}-confirm-error`;
  const formErrorId = `${ids}-form-error`;

  const messageFor = (scope: Scope): string | null =>
    error !== null && error.scope === scope ? error.message : null;

  const goto = (next: Step) => {
    setError(null);
    setStep(next);
  };

  const onUpload = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const picked = new FormData(event.currentTarget).get(FILE_FIELD);
    // Nothing new in the input is not the same as nothing chosen: coming back to
    // step one remounts an empty Dropzone while the File is still held here.
    const chosen = picked instanceof File && picked.size > 0 ? picked : file;

    const fail = (message: string) => {
      setError({ scope: 'file', message });
      document.getElementById(dropzoneInputId(FILE_FIELD))?.focus();
    };

    if (chosen === null) return fail(COPY.noFile);
    if (chosen.size > MAX_UPLOAD_BYTES) return fail(COPY.tooBig);
    if (!looksReadable(chosen)) return fail(COPY.wrongKind);

    setFile(chosen);
    goto(1);
  };

  const onPlot = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const fail = (message: string) => {
      setError({ scope: 'area', message });
      document.getElementById(areaId)?.focus();
    };

    const typed = sqft.trim();
    if (typed.length === 0) return fail(COPY.areaMissing);
    if (!/^\d+$/.test(typed)) return fail(COPY.areaNotANumber);
    const value = Number(typed);
    if (value < MIN_SQFT || value > MAX_SQFT) return fail(COPY.areaImplausible);

    goto(2);
  };

  const onStart = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (inFlight.current) return;

    if (!confirmed) {
      setError({ scope: 'confirm', message: COPY.confirmMissing });
      return;
    }
    if (file === null) {
      // Only reachable if the held File was somehow lost; send them back rather
      // than POST an empty upload.
      setError({ scope: 'file', message: COPY.noFile });
      setStep(0);
      return;
    }

    inFlight.current = true;
    setPending(true);
    setError(null);

    const body = new FormData();
    body.set(FILE_FIELD, file);
    body.set('built_up_sqft', sqft.trim());

    let failure = COPY.failed;
    try {
      const response = await fetch(`/api/loans/${loan.loan_id}/boq`, { method: 'POST', body });
      const payload: unknown = await response.json().catch(() => null);
      const field = (key: string): unknown =>
        typeof payload === 'object' && payload !== null && key in payload
          ? (payload as Record<string, unknown>)[key]
          : undefined;

      if (response.ok) {
        const jobId = field('job_id');
        if (typeof jobId === 'string' && jobId.length > 0) {
          // push, not replace: Back should return to the wizard rather than skip
          // past it. `pending` and `inFlight` are deliberately left set — the
          // navigation is the completion, and re-enabling the button under a
          // leaving page invites a second POST.
          router.push(`/owner/loans/${loan.loan_id}/analyzing?job=${encodeURIComponent(jobId)}`);
          return;
        }
      } else if (response.status === 401) {
        // The session died under the wizard — the backend restarting is enough
        // to do it, since it signs cookies with a per-process key. Signing in
        // is the only remedy, so offer it instead of an error the reader can
        // do nothing with. `next` returns them here with the loan still open.
        router.push(`/login?next=${encodeURIComponent('/owner/onboarding')}`);
        return;
      } else if (response.status === 413) {
        failure = COPY.tooLarge;
      } else if (response.status < 500) {
        // A 4xx carries copy written for this reader ("Unsupported file type"),
        // so it is worth showing. A 5xx carries whatever the service happened
        // to say — an internal detail, sometimes an API instruction — and the
        // generic message is more honest than quoting it.
        const detail = field('detail');
        if (typeof detail === 'string' && detail.length > 0) failure = COPY.refused + detail;
      }
    } catch {
      // A refused connection or an aborted upload. `failure` is already the
      // generic message.
    }

    setError({ scope: 'form', message: failure });
    inFlight.current = false;
    setPending(false);
  };

  return (
    <>
      <ol className="mt-9 flex justify-center">
        {COPY.steps.map((label, index) => (
          <li
            key={label}
            aria-current={index === step ? 'step' : undefined}
            className="flex items-center"
          >
            <span
              className={`flex items-center gap-[9px] rounded-pill border px-4 py-2 ${
                index === step ? 'border-ink bg-ink' : 'border-line bg-card'
              }`}
            >
              <span
                aria-hidden="true"
                className={`tnum flex h-5 w-5 items-center justify-center rounded-full text-[11px] font-semibold ${
                  index === step ? 'bg-card text-ink' : 'bg-chip text-sub'
                }`}
              >
                {index + 1}
              </span>
              <span
                className={`text-[13px] font-semibold ${index === step ? 'text-bg' : 'text-sub'}`}
              >
                {label}
              </span>
            </span>
            {index < COPY.steps.length - 1 && (
              <span aria-hidden="true" className="h-px w-9 bg-input-border" />
            )}
          </li>
        ))}
      </ol>

      <Card className="mx-auto mt-7 w-full max-w-[640px] p-7">
        {step === 0 && (
          <form noValidate onSubmit={onUpload}>
            <Dropzone
              name={FILE_FIELD}
              accept={ACCEPT}
              label={COPY.dropLabel}
              hint={COPY.dropHint}
              describedBy={fileErrorId}
              invalid={messageFor('file') !== null}
            />
            {file !== null && (
              <p className="mt-3 text-[12.5px] text-sub">
                {COPY.held}
                <span className="font-semibold text-ink">{file.name}</span>
                {COPY.heldTail}
              </p>
            )}
            <p
              id={fileErrorId}
              role="alert"
              className="mt-2 text-[12px] font-semibold text-danger empty:hidden"
            >
              {messageFor('file')}
            </p>
            <div className="mt-4 flex items-center justify-between gap-4 text-[12.5px] text-faint">
              <span>{COPY.volumeNote}</span>
              {/* The prototype's dead `href="#"`, given the real destination —
                  but only for the owner it is actually reachable for. Every other
                  session crosses the loan boundary, and `proxy.ts` answers that
                  with a redirect to /login: a link labelled "see a sample report"
                  that signs the reader out and discards the file they had just
                  chosen is worse than no link at all. */}
              {loan.loan_id === GOLDEN_CASE_LOAN_ID && (
                <span className="tnum">
                  {COPY.sampleLead}
                  <Link
                    href={`/owner/loans/${GOLDEN_CASE_LOAN_ID}/boq`}
                    className="font-semibold text-action hover:underline"
                  >
                    {COPY.sampleLink}
                  </Link>
                </span>
              )}
            </div>
            <div className="mt-6 flex justify-end">
              <Button type="submit" variant="primary">
                {COPY.next}
              </Button>
            </div>
          </form>
        )}

        {step === 1 && (
          <form noValidate onSubmit={onPlot}>
            <h2 className="font-display text-[19px] font-bold text-ink">{COPY.plotTitle}</h2>
            <p className="mt-2 text-[13px] leading-[1.6] text-sub">{COPY.plotLead}</p>

            <dl className="mt-5 flex flex-col gap-[10px]">
              <div className="flex items-baseline justify-between gap-3">
                <dt className="text-[12.5px] text-sub">{COPY.plotLabel}</dt>
                <dd className="text-[13px] font-semibold text-ink">
                  {loan.plot_label ?? loan.locality}
                </dd>
              </div>
              <div className="flex items-baseline justify-between gap-3">
                <dt className="text-[12.5px] text-sub">{COPY.localityLabel}</dt>
                <dd className="text-[13px] font-semibold text-ink">{loan.locality}</dd>
              </div>
            </dl>

            <label htmlFor={areaId} className="mt-5 block text-[12.5px] font-semibold text-sub">
              {COPY.areaLabel}
            </label>
            <p id={areaHintId} className="mt-1 text-[11.5px] text-faint">
              {COPY.areaHint}
            </p>
            <div className="mt-2 flex items-center gap-2">
              <input
                id={areaId}
                name="built_up_sqft"
                type="text"
                inputMode="numeric"
                autoComplete="off"
                value={sqft}
                onChange={(event) => setSqft(event.target.value)}
                aria-describedby={`${areaHintId} ${areaErrorId}`}
                aria-invalid={messageFor('area') !== null || undefined}
                className="tnum w-[160px] rounded-[10px] border border-input-border bg-card px-[14px] py-[11px] text-[13.5px] text-ink placeholder:text-faint"
              />
              <span className="text-[12.5px] text-sub">{COPY.areaUnit}</span>
            </div>
            <p
              id={areaErrorId}
              role="alert"
              className="mt-2 text-[12px] font-semibold text-danger empty:hidden"
            >
              {messageFor('area')}
            </p>

            <div className="mt-6 flex justify-between">
              <Button variant="ghost" onClick={() => goto(0)}>
                {COPY.back}
              </Button>
              <Button type="submit" variant="primary">
                {COPY.next}
              </Button>
            </div>
          </form>
        )}

        {step === 2 && (
          <form noValidate onSubmit={onStart}>
            <h2 className="font-display text-[19px] font-bold text-ink">{COPY.loanTitle}</h2>
            <p className="mt-2 text-[13px] leading-[1.6] text-sub">{COPY.loanLead}</p>

            <dl className="mt-5 flex flex-col gap-[10px]">
              <div className="flex items-baseline justify-between gap-3">
                <dt className="text-[12.5px] text-sub">{COPY.sanctionedLabel}</dt>
                <dd className="tnum text-[13.5px] font-medium text-ink">
                  {formatINR(loan.sanctioned)}
                </dd>
              </div>
              <div className="flex items-baseline justify-between gap-3">
                <dt className="text-[12.5px] text-sub">{COPY.drawnLabel}</dt>
                <dd className="tnum text-[13.5px] font-medium text-ink">
                  {formatINR(loan.disbursed)}
                </dd>
              </div>
              <div className="flex items-baseline justify-between gap-3">
                <dt className="text-[12.5px] text-sub">{COPY.areaLabel}</dt>
                <dd className="tnum text-[13.5px] font-medium text-ink">
                  {`${formatQty(Number(sqft))} ${COPY.areaUnit}`}
                </dd>
              </div>
              <div className="flex items-baseline justify-between gap-3">
                <dt className="text-[12.5px] text-sub">{COPY.contractorLabel}</dt>
                <dd className="text-[13px] font-semibold text-ink">
                  {loan.contractor ?? COPY.contractorUnknown}
                </dd>
              </div>
            </dl>

            <label className="mt-5 flex items-start gap-[10px] text-[13px] text-ink">
              <input
                type="checkbox"
                name="confirm"
                checked={confirmed}
                onChange={(event) => setConfirmed(event.target.checked)}
                aria-describedby={confirmErrorId}
                aria-invalid={messageFor('confirm') !== null || undefined}
                className="accent-action mt-[2px] h-4 w-4 flex-none"
              />
              <span>{COPY.confirmLabel}</span>
            </label>
            <p
              id={confirmErrorId}
              role="alert"
              className="mt-2 text-[12px] font-semibold text-danger empty:hidden"
            >
              {messageFor('confirm')}
            </p>

            <div className="mt-6 flex justify-between">
              <Button variant="ghost" onClick={() => goto(1)} disabled={pending}>
                {COPY.back}
              </Button>
              <Button type="submit" variant="primary" disabled={pending} aria-busy={pending}>
                {pending ? COPY.starting : COPY.start}
              </Button>
            </div>
            <p
              id={formErrorId}
              role="alert"
              className="mt-3 text-center text-[12px] font-semibold text-danger empty:hidden"
            >
              {messageFor('form')}
            </p>
          </form>
        )}
      </Card>
    </>
  );
}
