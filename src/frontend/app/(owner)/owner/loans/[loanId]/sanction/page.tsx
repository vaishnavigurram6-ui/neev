// Sanction Check — `design_handoff_neev/Neev 2 Sanction Check.dc.html`.
//
// The one screen that answers the question the whole product exists for: will
// the sanctioned amount finish the house? Three comparison bars, the shortfall,
// the section-by-section gap, and the ways out of it.
//
// Data: `GET /api/loans/{id}/sanction-check` -> `SanctionCheckView`, plus
// `GET /api/loans/{id}` for the two loan facts the copy needs (the sanctioned
// amount in the headline and the locality in the sub-line). Nothing on this
// page is a literal figure — including the bar widths, which are `pct_of_max`.
//
// Ported, not transcribed, in three places:
//   * the mockup's QUOTED / MARKET / Δ legend sits *below* its rows; here it is
//     a real <thead> above them, because the kit's `CardTable` is what every
//     other grid in the product uses and column headers belong before the data
//     they name (spec §6.1a: where a screen and the kit disagree, the kit wins);
//   * the shortfall callout is a sibling of the bars card rather than a tinted
//     box inside it, so it can be the kit's `CalloutBanner` instead of a
//     one-off;
//   * the mockup has no empty and no error state, and no copy for a loan whose
//     sanction *does* cover its scope. Those three are authored here, in the
//     same voice, and marked below.
import { notFound } from 'next/navigation';
import CalloutBanner from '@/components/owner/CalloutBanner';
import SanctionBars from '@/components/owner/SanctionBars';
import SanctionOptions from '@/components/owner/SanctionOptions';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import CardTable, { type Column } from '@/components/ui/CardTable';
import EmptyState from '@/components/ui/EmptyState';
import Figure from '@/components/ui/Figure';
import PageHeader from '@/components/ui/PageHeader';
import StickyRail from '@/components/ui/StickyRail';
import { ApiError, apiGet } from '@/lib/api';
import { formatDelta, formatINR, formatPct } from '@/lib/format';
import type { SanctionCheckView, SanctionSectionView } from '@/lib/types';

/** U+2014. Stands in for a figure that does not exist — never a zero, and never
 *  a blank cell, which reads as "we forgot to fetch this". */
const EM_DASH = '—';

/** U+2212. The shortfall's share of the realistic cost is stated as a negative,
 *  matching both the mockup and `formatINR`'s true minus. `formatPct` has no
 *  sign of its own, so the sign is applied here — to a share that is only ever
 *  rendered on the branch where the shortfall is positive. */
const MINUS = '−';

const COPY = {
  eyebrow: 'AT SANCTION',
  gapTitle: 'Where the gap comes from',
  gapEmpty: 'This analysis did not break the gap down by section.',
  meansEyebrow: 'WHAT THIS MEANS',
  shortfallLead: 'Shortfall of',
  shortfallTail: '— flagged before drawdown',
  shortfallBody:
    'At current rates, funds run out around brickwork. Re-scope now, while the plan can still change.',
  shortfallMeans: "The sanction won't reach a habitable structure as scoped.",
  waysTail: 'forward, in order of least pain:',
  ratesNote:
    'Rates: 32,963 real listings across six metros · CPWD DSR construction benchmarks · updated monthly.',
  // AUTHORED, not in the mockup: the mockup only draws loan 1001, which is
  // short. A loan whose sanction covers its scope still has to say so.
  coversLead: 'Your sanction covers this scope',
  coversTail: 'to spare',
  coversBody: "Nothing needs re-scoping today. We'll check again each time rates or the BoQ move.",
  coversMeans: 'The sanction reaches a habitable structure as scoped.',
  // AUTHORED, not in the mockup: no BoQ means there is nothing to re-price.
  emptyTitle: 'No BoQ to check yet',
  emptyBody:
    "Once your contractor's BoQ is in, we re-price every line at local rates and tell you whether the sanction reaches a finished house — before any money moves.",
  emptyAction: 'Upload the BoQ',
};

/** "three ways forward" is a count of the rows below it, so it is derived. A
 *  hardcoded "Three" would be a figure in the JSX, and would go quietly wrong
 *  the day a loan gets two routes instead of three. */
const COUNT_WORDS = ['No', 'One', 'Two', 'Three', 'Four', 'Five', 'Six'];

/** The table's accessible description. The locality is the loan's, not a
 *  constant — this screen is the same screen in Kompally and in Kondapur. */
function gapCaption(locality: string): string {
  return `Each part of the gap between the quote and the market: what the contractor quoted for it, what it costs at ${locality} rates, and the difference.`;
}

function waysForwardLead(count: number): string {
  const word = COUNT_WORDS[count] ?? String(count);
  return `${word} ${count === 1 ? 'way' : 'ways'} ${COPY.waysTail}`;
}

const COLUMNS: Column<SanctionSectionView>[] = [
  {
    key: 'name',
    header: 'Section',
    render: (row) => <span className="font-medium text-ink">{row.name}</span>,
  },
  {
    key: 'quoted',
    header: 'Quoted',
    align: 'right',
    width: '120px',
    // Two of the five rows have no quoted figure at all — one was never in the
    // BoQ, one was left unstated. The API carries that as `quoted: null` plus a
    // note in the contractor's own terms; printing ₹0 there would invent a
    // quote, and an empty cell would look like a bug.
    render: (row) =>
      row.quoted === null ? (
        <span className="text-[12.5px] text-faint">{row.quoted_note ?? EM_DASH}</span>
      ) : (
        <Figure value={formatINR(row.quoted)} size="sm" />
      ),
  },
  {
    key: 'market',
    header: 'Market',
    align: 'right',
    width: '120px',
    render: (row) =>
      row.market === null ? (
        <span className="text-[12.5px] text-faint">{EM_DASH}</span>
      ) : (
        <Figure value={formatINR(row.market)} size="sm" />
      ),
  },
  {
    key: 'delta',
    header: 'Δ',
    align: 'right',
    width: '100px',
    render: (row) => <Figure value={formatDelta(row.delta)} tone={row.tone} size="sm" />,
  },
];

/** The subset of the backend's `LoanSummaryView` this screen reads.
 *
 *  `lib/types.ts` is frozen for this phase and stops at the sanction, tranche
 *  and portfolio views — it never got `LoanSummaryView`, so there is nothing to
 *  import. Declared narrow and local rather than added to the frozen file;
 *  reconcile with `npm run gen:types` when the generated types land. */
interface LoanFacts {
  loan_id: string;
  locality: string;
  sanctioned: number;
}

async function loadLoan(loanId: string): Promise<LoanFacts> {
  try {
    return await apiGet<LoanFacts>(`/api/loans/${encodeURIComponent(loanId)}`);
  } catch (cause) {
    // No such loan is a 404 page, not an error boundary. Anything else — an
    // unreachable backend, a 500 — is a real failure and belongs in error.tsx.
    if (cause instanceof ApiError && cause.status === 404) notFound();
    throw cause;
  }
}

/** `null` when the loan has no analysed BoQ. The backend answers 404 for that,
 *  which is a legitimate state of a real loan (nine of the ten seeded loans are
 *  in it), so it renders as empty rather than as a failure. */
async function loadSanction(loanId: string): Promise<SanctionCheckView | null> {
  try {
    return await apiGet<SanctionCheckView>(
      `/api/loans/${encodeURIComponent(loanId)}/sanction-check`
    );
  } catch (cause) {
    if (cause instanceof ApiError && cause.status === 404) return null;
    throw cause;
  }
}

export default async function SanctionCheckPage({
  params,
}: {
  params: Promise<{ loanId: string }>;
}) {
  const { loanId } = await params;
  const [loan, view] = await Promise.all([loadLoan(loanId), loadSanction(loanId)]);

  const header = (
    <PageHeader
      eyebrow={COPY.eyebrow}
      title={`Will ${formatINR(loan.sanctioned)} finish this house?`}
      sub={`Your BoQ scope, re-priced at today's ${loan.locality} rates — before any money moves.`}
    />
  );

  if (view === null) {
    return (
      <div className="flex flex-col gap-5">
        {header}
        <EmptyState
          title={COPY.emptyTitle}
          body={COPY.emptyBody}
          action={
            <Button href={`/owner/loans/${loan.loan_id}/boq`} variant="primary">
              {COPY.emptyAction}
            </Button>
          }
        />
      </div>
    );
  }

  const short = view.shortfall > 0;
  // The shortfall as a share of the largest bar — the realistic cost — which is
  // the mockup's −20% (7,00,000 of 35,00,000). Derived, never spelled.
  const largest = view.bars.reduce((max, bar) => Math.max(max, bar.value), 0);
  const share = largest > 0 ? Math.abs(view.shortfall) / largest : 0;

  return (
    <div className="flex flex-col gap-5">
      {header}

      <div className="flex items-start gap-5">
        {/* min-w-0 so the gap table scrolls inside its own container instead of
            pushing the page body sideways below 1280px. */}
        <div className="flex min-w-0 flex-1 flex-col gap-5">
          <Card className="p-6">
            <SanctionBars bars={view.bars} />
          </Card>

          <CalloutBanner
            tone={short ? 'danger' : 'success'}
            lead={
              short
                ? `${COPY.shortfallLead} ${formatINR(view.shortfall)} ${COPY.shortfallTail}`
                : `${COPY.coversLead} — ${formatINR(-view.shortfall)} ${COPY.coversTail}.`
            }
            body={short ? COPY.shortfallBody : COPY.coversBody}
            action={
              <Figure
                value={`${short ? MINUS : '+'}${formatPct(share)}`}
                tone={short ? 'danger' : 'success'}
                size="lg"
              />
            }
          />

          <section className="flex flex-col gap-3">
            <h2 className="text-[14.5px] font-bold text-ink">{COPY.gapTitle}</h2>
            <CardTable
              columns={COLUMNS}
              rows={view.sections}
              caption={gapCaption(loan.locality)}
              emptyMessage={COPY.gapEmpty}
            />
          </section>
        </div>

        <StickyRail>
          <Card className="px-6 py-[22px]">
            <p className="text-[12px] font-semibold uppercase tracking-[0.08em] text-faint">
              {COPY.meansEyebrow}
            </p>
            <h2 className="mt-[10px] text-[19px] font-bold leading-[1.4] text-ink">
              {short ? COPY.shortfallMeans : COPY.coversMeans}
            </h2>
            {view.options.length > 0 && (
              <p className="mt-[10px] text-[13px] leading-[1.6] text-sub">
                {waysForwardLead(view.options.length)}
              </p>
            )}
          </Card>

          <SanctionOptions options={view.options} />

          <p className="px-1 text-[12px] leading-[1.6] text-faint">{COPY.ratesNote}</p>
        </StickyRail>
      </div>
    </div>
  );
}
