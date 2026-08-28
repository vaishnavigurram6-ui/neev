// Bank Onboarding — Neev 7 Bank Onboarding.dc.html.
//
// Scaffolded preview (plan Task 19). Setup owns the thresholds that drive every
// recommendation in the console, which is why it stays in the bank nav on all
// bank routes (spec §7.3) even though the mockups deleted it from three of the
// four bank screens.
//
// Step 3 is a real <form> with labelled controls — a number input for the
// exposure hold threshold, a number input for the before-slab share, and a
// <select> for the confidence floor. The prototype draws all three as styled
// divs. Saving needs a settings endpoint that no task in this phase builds, so
// the submit button is disabled and says why rather than silently doing nothing.
import { SETUP } from '@/components/bank/preview';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import Dropzone from '@/components/ui/Dropzone';
import PageHeader from '@/components/ui/PageHeader';
import StatusPill from '@/components/ui/StatusPill';
import { formatRatio } from '@/lib/format';

const COPY = {
  eyebrow: 'SETUP · STEP 1 OF 3',
  title: 'Bring your construction book onto Neev',
  sub: 'Three steps: add your loans, invite your borrowers, set your risk thresholds. Most books are live the same day.',

  uploadTitle: 'Upload your draw schedule',
  uploadBody:
    'One CSV or Excel — loan IDs, sanctions, tranches, milestones. We map the columns automatically.',
  uploadLabel: 'Upload CSV / XLSX',
  uploadHint: 'Drop the draw schedule here, or choose a file.',
  uploadedTail: ' loans on the book · columns mapped on upload',

  losTitle: 'Connect your LOS / core banking',
  losBody:
    "Loans sync automatically as they're sanctioned; disbursements flow back as decisions are made.",
  losCta: 'Request API access',
  losNote: 'Finflux, Pennant, custom REST',
  losWhy: 'The LOS connector is not part of this build — the seam is here, the integration is not.',

  singleTitle: 'Add a single loan',
  singleBody:
    'Borrower, plot, sanction, tranche plan — five fields. Good for a pilot on one branch’s loans.',
  singleCta: 'Add loan manually',
  singleNote: '~2 minutes per loan',
  singleWhy: 'Adding a loan by hand needs a loan-creation endpoint, which this preview screen does not have yet.',

  inviteTitle: 'Invite your borrowers',
  inviteBody:
    'Each borrower gets a WhatsApp/SMS link to upload their BoQ and monthly site photos — no app install. Their uploads become your verification evidence, and their contract gets audited for free: fewer stalled builds on your book.',
  inviteCtaLead: 'Send all ',
  inviteWhy: 'Sending invites needs the messaging integration, which is out of scope for this build.',

  thresholdsTitle: 'Set your thresholds',
  exposureLabel: 'Hold when exposure exceeds',
  slabLabel: 'Flag payment schedules above (before slab)',
  confidenceLabel: 'Escalate to physical visit below confidence',
  thresholdsNote:
    'Defaults follow standard QS practice. The statutory site valuation stays — Neev triages which visits happen first, never replaces them.',
  save: 'Save thresholds',
  saveWhy:
    'Saving thresholds needs a settings endpoint, which this preview screen does not have yet.',

  skip: 'Skip for now',
  finish: 'Finish setup → Portfolio',
};

const PORTFOLIO_HREF = '/bank/portfolio';

const FIELD_CLASS =
  'tnum w-[104px] rounded-bank border border-input-border bg-chip px-3 py-[5px] text-right text-[13px] font-semibold text-ink';

export default function BankSetupPage() {
  const inviteLink = `${SETUP.invitePrefix}${SETUP.inviteLoanId}`;

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        eyebrow={COPY.eyebrow}
        title={COPY.title}
        sub={COPY.sub}
        actions={<StatusPill tone="neutral" label="Preview" skin="bank" />}
      />

      <div className="grid grid-cols-3 gap-[14px]">
        <Card skin="bank" className="flex flex-col gap-[10px] p-[22px]">
          <div className="flex items-start justify-between gap-3">
            <h2 className="text-[15px] font-bold text-ink">{COPY.uploadTitle}</h2>
            <StatusPill tone="neutral" label="RECOMMENDED" skin="bank" size="sm" />
          </div>
          <p className="text-[12.5px] leading-[1.6] text-sub">{COPY.uploadBody}</p>
          <Dropzone
            name="draw_schedule"
            accept=".csv,.xlsx,.xls,text/csv"
            label={COPY.uploadLabel}
            hint={COPY.uploadHint}
          />
          <p className="tnum text-[11px] text-faint">
            {`${SETUP.loanCount}${COPY.uploadedTail}`}
          </p>
        </Card>

        <Card skin="bank" className="flex flex-col gap-[10px] p-[22px]">
          <h2 className="text-[15px] font-bold text-ink">{COPY.losTitle}</h2>
          <p className="text-[12.5px] leading-[1.6] text-sub">{COPY.losBody}</p>
          <div className="mt-auto flex flex-col gap-[10px] pt-[6px]">
            <Button
              skin="bank"
              disabled
              title={COPY.losWhy}
              aria-describedby="los-why"
              className="w-full"
            >
              {COPY.losCta}
            </Button>
            <p className="text-[11px] text-faint">{COPY.losNote}</p>
            {/* Disabled controls are out of the tab order and `title` is not
                reliably announced, so every reason is on the page as text. */}
            <p id="los-why" className="text-[11px] text-faint">
              {COPY.losWhy}
            </p>
          </div>
        </Card>

        <Card skin="bank" className="flex flex-col gap-[10px] p-[22px]">
          <h2 className="text-[15px] font-bold text-ink">{COPY.singleTitle}</h2>
          <p className="text-[12.5px] leading-[1.6] text-sub">{COPY.singleBody}</p>
          <div className="mt-auto flex flex-col gap-[10px] pt-[6px]">
            <Button
              skin="bank"
              disabled
              title={COPY.singleWhy}
              aria-describedby="single-why"
              className="w-full"
            >
              {COPY.singleCta}
            </Button>
            <p className="text-[11px] text-faint">{COPY.singleNote}</p>
            <p id="single-why" className="text-[11px] text-faint">
              {COPY.singleWhy}
            </p>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-2 gap-[14px]">
        <Card skin="bank" className="p-[22px]">
          <div className="flex items-center gap-[10px]">
            <span
              aria-hidden="true"
              className="tnum flex h-[24px] w-[24px] flex-none items-center justify-center rounded-full bg-chip text-[12px] text-sub"
            >
              2
            </span>
            <h2 className="text-[15px] font-bold text-ink">{COPY.inviteTitle}</h2>
          </div>
          <p className="mt-[10px] text-[12.5px] leading-[1.65] text-sub">{COPY.inviteBody}</p>
          <div className="mt-[14px] flex items-center gap-2">
            <span className="tnum flex-1 rounded-bank bg-chip px-[14px] py-[10px] text-[12px] text-sub">
              {inviteLink}
            </span>
            <Button
              skin="bank"
              disabled
              title={COPY.inviteWhy}
              aria-describedby="invite-why"
            >
              {`${COPY.inviteCtaLead}${SETUP.loanCount}`}
            </Button>
          </div>
          <p id="invite-why" className="mt-[8px] text-[11px] text-faint">
            {COPY.inviteWhy}
          </p>
        </Card>

        <Card skin="bank" className="p-[22px]">
          <div className="flex items-center gap-[10px]">
            <span
              aria-hidden="true"
              className="tnum flex h-[24px] w-[24px] flex-none items-center justify-center rounded-full bg-chip text-[12px] text-sub"
            >
              3
            </span>
            <h2 className="text-[15px] font-bold text-ink">{COPY.thresholdsTitle}</h2>
          </div>

          <form className="mt-[14px] flex flex-col gap-3">
            <div className="flex items-center justify-between gap-3">
              <label htmlFor="exposure-hold" className="text-[13px] text-ink">
                {COPY.exposureLabel}
              </label>
              <input
                id="exposure-hold"
                name="exposure_hold"
                type="number"
                inputMode="decimal"
                step="0.01"
                min="0"
                defaultValue={formatRatio(SETUP.exposureHold)}
                className={FIELD_CLASS}
              />
            </div>

            <div className="flex items-center justify-between gap-3">
              <label htmlFor="pct-before-slab" className="text-[13px] text-ink">
                {COPY.slabLabel}
              </label>
              <div className="flex flex-none items-center gap-[6px]">
                <input
                  id="pct-before-slab"
                  name="pct_before_slab"
                  type="number"
                  inputMode="numeric"
                  step="1"
                  min="0"
                  max="100"
                  defaultValue={Math.round(SETUP.pctBeforeSlab * 100)}
                  className={FIELD_CLASS}
                />
                <span aria-hidden="true" className="text-[12px] text-faint">
                  %
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between gap-3">
              <label htmlFor="confidence-floor" className="text-[13px] text-ink">
                {COPY.confidenceLabel}
              </label>
              <select
                id="confidence-floor"
                name="confidence_floor"
                defaultValue={SETUP.confidenceFloor}
                className="rounded-bank border border-input-border bg-chip px-3 py-[5px] text-[13px] font-semibold text-ink"
              >
                {SETUP.confidenceOptions.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </div>

            <p className="text-[11.5px] leading-[1.6] text-faint">{COPY.thresholdsNote}</p>

            <div className="flex items-center justify-end gap-3">
              <p id="save-why" className="text-[11px] text-faint">
                {COPY.saveWhy}
              </p>
              <Button
                skin="bank"
                type="submit"
                disabled
                title={COPY.saveWhy}
                aria-describedby="save-why"
              >
                {COPY.save}
              </Button>
            </div>
          </form>
        </Card>
      </div>

      <div className="flex justify-end gap-[10px]">
        <Button href={PORTFOLIO_HREF} skin="bank">
          {COPY.skip}
        </Button>
        <Button href={PORTFOLIO_HREF} skin="bank" variant="primary">
          {COPY.finish}
        </Button>
      </div>
    </div>
  );
}
