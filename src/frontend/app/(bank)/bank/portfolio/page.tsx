// Portfolio Hotlist — ported from `design_handoff_neev/Neev 4 Portfolio Hotlist.dc.html`.
//
// The book, ranked worst-first. Everything on the page comes from
// `GET /api/portfolio?filter=` — the four cards, the ten rows, each row's tone,
// and each row's drill-in href. The prototype's `mk()` helper hand-colours every
// figure with a hex pair and points nine of its ten rows at `href="#"`; both are
// fragment artifacts. The API supplies `tone` (one vocabulary) and a real `href`
// per row, so the officer can open any loan in the book, not just the demo one.
//
// `?filter=` is a query param rather than component state so a credit officer can
// send a colleague a link that reproduces exactly what they were looking at
// (spec §6.6). It is validated here and passed through to the API, which owns
// what "needs action" means.
import { formatByKind } from '@/components/bank/kindFormat';
import Button from '@/components/ui/Button';
import CardTable, { type Column } from '@/components/ui/CardTable';
import EmptyState from '@/components/ui/EmptyState';
import Figure from '@/components/ui/Figure';
import PageHeader from '@/components/ui/PageHeader';
import SegmentedToggle, { type ToggleOption } from '@/components/ui/SegmentedToggle';
import StatCard from '@/components/ui/StatCard';
import StatusPill from '@/components/ui/StatusPill';
import { apiGet } from '@/lib/api';
import { formatDelta, formatINR, formatRatio } from '@/lib/format';
import { toneClasses } from '@/lib/tone';
import type { PortfolioRowView, PortfolioView } from '@/lib/types';

const COPY = {
  eyebrow: 'Portfolio hotlist',
  title: 'Construction portfolio',
  rankedBy: 'ranked by disbursement exposure',
  export: 'Export',
  // Nothing in the API generates a file, and a control that silently does
  // nothing is worse than one that says why. Spec §10 keeps document generation
  // out of this build.
  exportWhy: 'Exporting the book to a file is out of scope for this build (spec §10).',
  filterLabel: 'Which loans to show',
  caption:
    'Every loan on the book, ranked worst-first by disbursement exposure, with what has been paid, what has been seen on site, and the action each loan needs.',
  definitions:
    'Exposure = cumulative disbursed ÷ verified value in place · CTC gap = undrawn balance − cost to complete at current rates',
  provenance: 'illustrative draw schedule',
  behind: 'Behind schedule.',
  emptyTitle: 'No loans match this filter',
  emptyBody:
    'Nothing on the book needs this attention right now. Switch back to All to see every active loan.',
};

const FILTERS: ToggleOption[] = [
  { value: 'all', label: 'All' },
  { value: 'needs_action', label: 'Needs action' },
  { value: 'on_track', label: 'On track' },
];

const COLUMNS: Column<PortfolioRowView>[] = [
  {
    key: 'loan',
    header: 'Loan',
    width: '92px',
    render: (row) => <Figure value={row.loan_id} size="sm" />,
  },
  {
    key: 'borrower',
    header: 'Borrower · Location',
    // The row's drill-in. The borrower's name rather than the loan id: it is
    // the biggest target in the row, it is what an officer is looking for, and
    // a link whose whole text is four digits tells a screen reader nothing
    // about where it goes.
    render: (row) => (
      <span className="text-[13px] text-ink">
        <b className="text-action underline decoration-1 underline-offset-2">{row.borrower}</b>{' '}
        <span className="text-faint">{`· ${row.locality}`}</span>
        <span className="sr-only">{` — open the loan file for ${row.borrower}`}</span>
      </span>
    ),
  },
  {
    key: 'paid_up_to',
    header: 'Paid up to',
    width: '130px',
    render: (row) => <span className="text-[13px] text-sub">{row.paid_up_to}</span>,
  },
  {
    key: 'seen_on_site',
    header: 'Seen on site',
    width: '130px',
    // A row behind schedule is the whole point of the column, so it reads
    // differently in weight and in words, never in colour alone.
    render: (row) =>
      row.behind_schedule ? (
        <span className={`text-[13px] font-semibold ${toneClasses('danger', 'bank').text}`}>
          {row.seen_on_site}
          <span className="sr-only">{` ${COPY.behind}`}</span>
        </span>
      ) : (
        <span className="text-[13px] text-sub">{row.seen_on_site}</span>
      ),
  },
  {
    key: 'disbursed',
    header: 'Disbursed',
    align: 'right',
    width: '120px',
    render: (row) => <Figure value={formatINR(row.disbursed)} size="sm" skin="bank" />,
  },
  {
    key: 'exposure',
    header: 'Exposure',
    align: 'right',
    width: '100px',
    // The prototype colours this against two hardcoded thresholds (1.1 and
    // 0.95). Those literals do not exist in the API, and inventing them here
    // would put the frontend in the business of deciding what a safe exposure
    // is. The row's own tone — the tone of the recommendation this exposure
    // produced — carries the same signal and stays in one vocabulary.
    render: (row) => (
      <Figure value={formatRatio(row.exposure)} tone={row.tone} skin="bank" />
    ),
  },
  {
    key: 'gap',
    header: 'CTC gap',
    align: 'right',
    width: '120px',
    // `gap: null` is a closed loan, not a zero: it renders the API's own note
    // ("closed") in neutral, never "₹0" and never a green pass.
    render: (row) =>
      row.gap === null ? (
        <span className="text-[12.5px] text-faint">{row.gap_note ?? '—'}</span>
      ) : (
        <Figure
          value={formatDelta(row.gap)}
          tone={row.gap < 0 ? 'danger' : 'success'}
          size="sm"
          skin="bank"
        />
      ),
  },
  {
    key: 'action',
    header: 'Action',
    align: 'right',
    width: '110px',
    render: (row) => <StatusPill tone={row.tone} label={row.action_label} skin="bank" />,
  },
];

function filterFrom(raw: string | string[] | undefined): string {
  const value = Array.isArray(raw) ? raw[0] : raw;
  // An unknown `?filter=` falls back to "all" rather than 404-ing: the recipient
  // of a stale link sees the whole book with All highlighted, which is coherent,
  // and the API answers 422 for anything but the three so it is never forwarded.
  return FILTERS.some((option) => option.value === value) ? (value as string) : 'all';
}

export default async function PortfolioHotlistPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const filter = filterFrom((await searchParams).filter);
  // A backend that is down, slow or refusing throws ApiError; error.tsx renders
  // it as a retryable failure rather than an empty table that reads as "no loans".
  const view = await apiGet<PortfolioView>(`/api/portfolio?filter=${filter}`);

  const shown = view.rows.length;

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        eyebrow={COPY.eyebrow}
        title={COPY.title}
        sub={
          filter === 'all'
            ? `${shown} active loans, ${COPY.rankedBy}`
            : `${shown} of the book, ${COPY.rankedBy}`
        }
        actions={
          <>
            <div className="self-center">
              <SegmentedToggle
                options={FILTERS}
                value={filter}
                paramName="filter"
                skin="bank"
                label={COPY.filterLabel}
              />
            </div>
            <div className="flex max-w-[260px] flex-col items-end">
              {/* Disabled, and it says why in text a keyboard and a screen
                  reader both reach — a `title` alone reaches neither. */}
              <Button
                disabled
                skin="bank"
                title={COPY.exportWhy}
                aria-describedby="export-why"
                className="py-[8px] text-[12.5px]"
              >
                {COPY.export}
              </Button>
              <p id="export-why" className="mt-[6px] text-right text-[11px] text-faint">
                {COPY.exportWhy}
              </p>
            </div>
          </>
        }
      />

      <div className="grid grid-cols-4 gap-3">
        {view.cards.map((card) => (
          <StatCard
            key={card.label}
            label={card.label}
            value={formatByKind(card.value, card.value_kind)}
            sub={card.sub}
            tone={card.tone}
            skin="bank"
          />
        ))}
      </div>

      {shown === 0 ? (
        <EmptyState title={COPY.emptyTitle} body={COPY.emptyBody} skin="bank" />
      ) : (
        <CardTable
          columns={COLUMNS}
          rows={view.rows}
          skin="bank"
          caption={COPY.caption}
          rowHref={(row) => row.href}
          rowHrefColumn="borrower"
          // The prototype tints the rows that stop a release. Same intent, one
          // vocabulary: the tint is the row's own tone, and only where the tone
          // means something needs doing.
          rowTone={(row) => (row.tone === 'danger' || row.tone === 'warn' ? row.tone : null)}
        />
      )}

      <div className="flex justify-between gap-6 text-[12px] text-faint">
        <span>{COPY.definitions}</span>
        <span className="flex-none">{`${shown} loans · ${COPY.provenance}`}</span>
      </div>
    </div>
  );
}
