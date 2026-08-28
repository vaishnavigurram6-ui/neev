// Tranche Decision — ported from `design_handoff_neev/Neev 3 Tranche Decision.dc.html`.
//
// The one screen in the product where a lender changes something. Everything on
// it — the request amount, the five stages, the five math lines and their
// calculations, the photo captions and their checks, both narratives — comes from
// `GET /api/loans/{id}/tranches/{n}`. Not one figure is written here.
//
// The prototype puts loan 1001's pending request at tranche 3 and labels it
// "slab", but its own arithmetic contradicts that: the gap row reads
// `(28,00,000 − 18,00,000) − 15,80,000`, which only balances if T3 has already
// gone out. Resolved on 2026-08-28 in favour of the arithmetic — T1–T3 are paid
// and the pending request is T4, brickwork and roof, ₹4,40,000. Every headline
// figure is unchanged. Nothing in this file assumes a tranche number: the
// hotlist's own `href` says which tranche is awaiting a decision.
//
// `?rationale=` is in the URL for the same reason `?filter=` is on the hotlist —
// a link an officer sends reproduces the panel the sender was reading.
import Link from 'next/link';
import { notFound } from 'next/navigation';
import Panel from '@/components/owner/Panel';
import Card from '@/components/ui/Card';
import PageHeader from '@/components/ui/PageHeader';
import SegmentedToggle, { type ToggleOption } from '@/components/ui/SegmentedToggle';
import StageStrip from '@/components/ui/StageStrip';
import StatusPill from '@/components/ui/StatusPill';
import StickyRail from '@/components/ui/StickyRail';
import { ApiError, apiGet } from '@/lib/api';
import { formatINR, formatRatio } from '@/lib/format';
import { toneClasses, type Tone } from '@/lib/tone';
import type { TrancheDecisionView } from '@/lib/types';
import DecisionCard from './DecisionCard';
import EvidenceGrid, { evidenceChips } from './EvidenceGrid';
import MathTable from './MathTable';
import type { DecisionAction } from './state';

const COPY = {
  portfolio: 'Portfolio',
  requestLead: 'Release request —',
  drawnLead: 'Disbursed —',
  upcomingLead: 'Next draw —',
  requestAt: 'at',
  sub: 'site photos read against BoQ line items',
  settledTitle: 'No decision to take',
  paidBody:
    'This tranche has already been disbursed. The evidence and the exposure math above are the record of it.',
  upcomingBody:
    'This draw has not been requested yet. The decision card opens when the borrower submits it with the site photos for the stage.',
  recommend: 'Recommend',
  exposureLead: 'exposure',
  exposureUndefined: 'exposure undefined — no verified value in place',
  evidenceTitle: 'Site evidence — what the photos show',
  confidenceLead: 'Confidence:',
  humanReview: 'Needs human review',
  noPhotos: 'No photographs were submitted with this request.',
  mathTitle: 'The math, in one line each',
  mathCaption:
    'Each figure behind the recommendation: what it is, how it is worked out, and what it comes to.',
  rationaleLabel: 'Whose explanation to show',
  noRationale: 'No written explanation was recorded for this tranche.',
};

const RATIONALES: ToggleOption[] = [
  { value: 'owner', label: 'For the owner' },
  { value: 'officer', label: 'For the credit officer' },
];

// The milestone as the mockup's headline writes it, lower case and mid-sentence:
// "Release request — ₹4,40,000 at brickwork and roof". Keys are the pipeline's
// own milestone values; anything unrecognised falls back to itself, so a new
// milestone reads a little flatly rather than not at all.
const MILESTONE: Record<string, string> = {
  foundation: 'foundation',
  plinth: 'plinth',
  slab: 'slab',
  brickwork_roof: 'brickwork and roof',
  finishing: 'finishing',
};

// The pipeline's confidence band, in the one tone vocabulary.
const CONFIDENCE_TONE: Record<string, Tone> = {
  high: 'success',
  medium: 'warn',
  low: 'danger',
};

// Which of the card's three buttons the recommendation points at. INSPECT maps
// to ESCALATE because "escalate to physical inspection" is what the card offers
// for it; the endpoint accepts only the three.
const RECOMMENDED_ACTION: Record<string, DecisionAction> = {
  RELEASE: 'RELEASE',
  HOLD: 'HOLD',
  ESCALATE: 'ESCALATE',
  INSPECT: 'ESCALATE',
};

/** A loan id is an opaque short token in this build ("1001"). Same guard as
 *  `actions.ts` — the read and the write agree on what a loan id may be. */
const LOAN_ID = /^[A-Za-z0-9_-]{1,16}$/;

function first(value: string | string[] | undefined): string {
  return Array.isArray(value) ? (value[0] ?? '') : (value ?? '');
}

export default async function TrancheDecisionPage({
  params,
  searchParams,
}: {
  params: Promise<{ loanId: string; n: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { loanId, n } = await params;
  // `parseInt` stops at the first non-digit, so "4abc" would otherwise render
  // tranche 4 under a URL that does not name it.
  const tranche = Number.parseInt(n, 10);
  if (!Number.isInteger(tranche) || tranche < 1 || String(tranche) !== n) notFound();
  // The loan id is interpolated into the API path, so it is checked on the read
  // side too, not only in the write action: "1001%3Ffoo%3D1" would otherwise
  // make the server fetch a path this URL does not name.
  if (!LOAN_ID.test(loanId)) notFound();

  const asked = first((await searchParams).rationale);
  const rationale = RATIONALES.some((option) => option.value === asked) ? asked : 'owner';

  let view: TrancheDecisionView;
  try {
    view = await apiGet<TrancheDecisionView>(`/api/loans/${loanId}/tranches/${tranche}`);
  } catch (cause) {
    // A loan or tranche that is not on the book is a 404 — not the error state,
    // which promises a retry that would fail identically.
    if (cause instanceof ApiError && cause.status === 404) notFound();
    throw cause;
  }

  // The banner says the API's own word — HOLD, RELEASE, INSPECT, ESCALATE — and
  // takes its tone from the API too. `recommendationTone()` is the portfolio
  // pill's vocabulary, where RELEASE reads "ON TRACK"; "RECOMMEND ON TRACK" is
  // not a sentence a credit note would carry.
  const banner = toneClasses(view.recommendation_tone, 'bank');
  // Only a tranche on hold is a draw awaiting a decision. The hotlist links to
  // whichever tranche is furthest along, and on most of the book that one is
  // already paid — so without this the header would call disbursed money a
  // "release request" and the card would offer to release it a second time.
  const pending = view.status === 'on_hold';
  const lead = pending
    ? COPY.requestLead
    : view.status === 'paid'
      ? COPY.drawnLead
      : COPY.upcomingLead;
  const chips = evidenceChips(view.photos);
  const rationaleText = rationale === 'officer' ? view.officer_view : view.owner_view;

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        eyebrow={
          <>
            <Link href="/bank/portfolio" className="text-bank-accent hover:underline">
              {COPY.portfolio}
            </Link>
            {` · Loan ${view.loan_id} — ${view.borrower} · Tranche ${view.tranche_number}`}
          </>
        }
        title={`${lead} ${formatINR(view.request_amount)} ${COPY.requestAt} ${
          MILESTONE[view.milestone] ?? view.milestone
        }`}
        sub={COPY.sub}
        actions={
          <div
            className={`flex flex-none items-center gap-[10px] rounded-bank border border-line px-5 py-3 ${banner.bg} ${banner.text}`}
          >
            <span aria-hidden="true" className="h-[10px] w-[10px] flex-none rounded-full bg-current" />
            <div>
              <div className="text-[16px] font-bold uppercase tracking-[0.02em]">
                {`${COPY.recommend} ${view.recommendation}`}
              </div>
              <div className="text-[12px] opacity-90">
                {/* Never `Infinity`, and never an undefined exposure dressed up
                    as a safe one: the API says which it is. */}
                {view.exposure_undefined || view.exposure === null
                  ? COPY.exposureUndefined
                  : `${COPY.exposureLead} ${formatRatio(view.exposure)}`}
              </div>
            </div>
          </div>
        }
      />

      <div className="flex items-start gap-5">
        <div className="flex min-w-0 flex-1 flex-col gap-5">
          <Panel
            title={COPY.evidenceTitle}
            skin="bank"
            aside={
              <span className="flex items-center gap-2">
                {view.confidence && (
                  <StatusPill
                    tone={CONFIDENCE_TONE[view.confidence] ?? 'neutral'}
                    label={`${COPY.confidenceLead} ${view.confidence.toUpperCase()}`}
                    skin="bank"
                  />
                )}
                {view.needs_human_review && (
                  <StatusPill tone="warn" label={COPY.humanReview} skin="bank" />
                )}
              </span>
            }
          >
            {view.photos.length === 0 ? (
              <p className="text-[13px] text-sub">{COPY.noPhotos}</p>
            ) : (
              <>
                <EvidenceGrid photos={view.photos} />
                {chips.length > 0 && (
                  <ul className="mt-[14px] flex flex-wrap gap-2">
                    {chips.map((chip) => (
                      <li key={chip.label}>
                        <StatusPill tone={chip.tone} label={chip.label} skin="bank" />
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}

            <div className="mt-[18px]">
              <StageStrip stages={view.stages} skin="bank" />
            </div>
          </Panel>

          <Panel title={COPY.mathTitle} skin="bank">
            <MathTable rows={view.math} caption={COPY.mathCaption} />
          </Panel>
        </div>

        {/* The kit's 340px rail, not the prototype's 380px: the two-column
            shells are one width across the product (spec 6.1a). */}
        <StickyRail>
          <Card skin="bank" className="p-[22px]">
            {/* The tabs are the panel's heading — which narrative you are
                reading is the tab that is selected, so a second heading
                repeating it would only be read twice. */}
            <SegmentedToggle
              options={RATIONALES}
              value={rationale}
              paramName="rationale"
              skin="bank"
              label={COPY.rationaleLabel}
            />
            <p className="mt-[14px] text-[13px] leading-[1.7] text-sub">
              {rationaleText ?? COPY.noRationale}
            </p>
          </Card>

          {pending ? (
            <DecisionCard
              loanId={view.loan_id}
              tranche={view.tranche_number}
              requestAmount={formatINR(view.request_amount)}
              recommended={RECOMMENDED_ACTION[view.recommendation] ?? null}
              recommendedTone={view.recommendation_tone}
            />
          ) : (
            <Card skin="bank" className="bg-bank-bar px-[22px] py-[20px]">
              <h2 className="text-[13.5px] font-bold text-bank-surface">{COPY.settledTitle}</h2>
              <p className="mt-2 text-[11.5px] leading-[1.6] text-bank-inactive">
                {view.status === 'paid' ? COPY.paidBody : COPY.upcomingBody}
              </p>
            </Card>
          )}
        </StickyRail>
      </div>
    </div>
  );
}
