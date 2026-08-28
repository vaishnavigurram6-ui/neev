// BoQ Review — Neev 1 BoQ Review.dc.html.
//
// The screen the demo turns on: the contractor's quote, checked line by line
// against local benchmarks. Layout, grouping and copy are the prototype's;
// every figure comes from `GET /api/loans/{id}/boq/latest` (`BoqReviewView`).
// Not one number is written into this file — see `figures.ts` for the two the
// view model does not carry and how they are derived from the ones it does.
//
// Two calls, not one. `/boq/latest` answers 404 both for a loan nobody has
// heard of and for a loan whose BoQ has not been analysed yet, and those are
// different screens: the first is a wrong link, the second is an honest "nothing
// yet". `GET /api/loans/{id}` separates them, and carries the locality the
// header's sub-line names. They are issued together, so the second is free.
//
// The prototype's own gaps, closed here: the toggle went nowhere and the pill
// colours were six inline hex pairs (now one `tone`); "Marked-up PDF" was a live
// control for a feature that does not exist (now disabled, with the reason as
// visible text); every control was a <div> (now buttons, links and a real table).
import Link from 'next/link';
import { notFound } from 'next/navigation';
import CalloutBanner from '@/components/owner/CalloutBanner';
import GuidanceList from '@/components/owner/GuidanceList';
import Panel from '@/components/owner/Panel';
import Button from '@/components/ui/Button';
import CardTable, { type Column } from '@/components/ui/CardTable';
import EmptyState from '@/components/ui/EmptyState';
import Figure from '@/components/ui/Figure';
import PageHeader from '@/components/ui/PageHeader';
import SegmentedToggle from '@/components/ui/SegmentedToggle';
import StatCard from '@/components/ui/StatCard';
import StatusPill from '@/components/ui/StatusPill';
import StickyRail from '@/components/ui/StickyRail';
import { ApiError, apiGet } from '@/lib/api';
import { formatINR, formatPct } from '@/lib/format';
import type { Tone } from '@/lib/tone';
import type { BoqReviewView, FlagRowView } from '@/lib/types';
import CopyQuestionsButton from './CopyQuestionsButton';
import PaymentScheduleBar from './PaymentScheduleBar';
import SendQuestionsForm from './SendQuestionsForm';
import {
  amountAfterSlab,
  countRows,
  formatDay,
  formatStatValue,
  gstUpperBound,
  paymentTone,
  rowFigures,
} from './figures';
import { shareMessage } from './message';

/** The one field this screen reads from `GET /api/loans/{id}` (`LoanSummaryView`).
 *
 *  TYPE GAP: `lib/types.ts` transcribes `views.py` only as far as
 *  `TrancheDecisionView` — `LoanSummaryView`, `BuildProgressView` and
 *  `ContractorScorecardView` are missing, and `lib/` is frozen for Phase 2, so
 *  the subset actually consumed is declared here rather than editing a file three
 *  other screens are also building against. Delete this when the type lands. */
interface LoanFacts {
  locality: string;
}

/** The payment split the mockup calls standard ("The standard is 25%"). A market
 *  convention quoted in the copy, not a figure about this loan — which is why it
 *  lives beside the sentence that states it. */
const STANDARD_PCT_BEFORE_SLAB = 0.25;

/** The top of the GST band the notice quotes ("At 12–18%"). Same reasoning: it is
 *  half of a sentence, and the rupee figure it produces is a fraction of the
 *  quoted total, which comes from the API. */
const GST_UPPER_RATE = 0.18;

const COPY = {
  eyebrow: 'BEFORE SIGNING',
  title: 'Your contract, checked line by line',
  received: 'received {day}',
  checked: '{n} items checked against {locality} benchmarks',

  markedUpPdf: 'Marked-up PDF',
  pdfWhy: 'A marked-up PDF of your BoQ is out of scope for this build (spec §10).',
  uploadRevised: 'Upload revised BoQ',
  // Neev does not message the contractor: WhatsApp sending is out of scope
  // (spec §10). The button records that these questions are ready and marks them
  // sent on the loan file; the owner copies the text and sends it themselves.
  // The old copy said "{n} questions are now with Sri Sai Constructions", which
  // claimed a delivery that never happened.
  send: 'Mark {n} questions as sent',
  sendAgain: 'Mark as sent again',
  sending: 'Saving…',
  sentOne: '1 question logged on your file, ready to send to',
  sentMany: '{n} questions logged on your file, ready to send to',
  withContractor: 'your contractor',
  sendNote: 'Neev does not message anyone for you — copy the text below and send it yourself.',

  attention: '{flagged} of {total} items need your attention',
  toggleLabel: 'Which BoQ lines to show',
  flagged: 'Flagged',
  all: 'All {n}',
  colItem: 'Item',
  colFinding: 'What we found',
  colFlag: 'Flag',
  expected: 'expected',
  countNoun: 'items',
  tableCaption:
    'Every BoQ line that needs your attention, grouped by section: the line’s own figures, what the local benchmark says, and the flag raised against it.',
  emptyTable: 'Nothing on this contract needs your attention.',
  matched: '{n} items matched local benchmarks',
  showAll: 'Show all',
  showFlagged: 'Show flagged only',
  allNote:
    'Only the {flagged} flagged lines are stored in this build, so this list is the same one. The other {matched} matched their {locality} benchmarks line for line.',

  payTitle: 'Payment schedule',
  frontLoaded: 'Front-loaded',
  standardSchedule: 'Standard',
  payBody: '{pct} is due before the slab is cast. The standard is {standard}.',
  payListLabel: 'Payment schedule, stage by stage',
  beforeSlab: 'before slab',
  afterSlab: 'after',

  questionsTitle: 'Send before you sign',
  questionsBody:
    'Questions, not accusations — each one your contractor can confirm in writing.',
  questionsSent: 'Sent',
  questionsDraft: 'Draft',
  copyCta: 'Copy as WhatsApp message',
  copied: 'Copied. Paste it into WhatsApp and send it.',
  copyManual:
    'Your browser would not let us copy it. The message is below — select it and copy it yourself.',
  copyManualLabel: 'The message to send your contractor',

  gstLead: 'GST is not mentioned anywhere.',
  gstBody: 'At 12–18% that is up to {amount} unbudgeted. Ask whether rates are inclusive.',
  gstBodyNoAmount:
    'At 12–18% of the quoted total that is a large unbudgeted amount. Ask whether rates are inclusive.',

  emptyTitle: 'No contract checked yet',
  emptyHeading: 'Nothing to check yet',
  emptyBody:
    'We have not received a BoQ for this loan. Upload your contractor’s quote and we will check every line against local benchmarks before you sign.',
  emptyCta: 'Upload your BoQ',
};

type FlaggedRow = FlagRowView & { group: string };

const COLUMNS: Column<FlaggedRow>[] = [
  {
    key: 'item',
    header: COPY.colItem,
    width: '64px',
    render: (row) => <Figure value={row.item} size="sm" />,
  },
  {
    key: 'finding',
    header: COPY.colFinding,
    render: (row) => {
      const figures = rowFigures(row, COPY.expected);
      return (
        <div>
          <div className="flex flex-wrap items-baseline gap-[10px]">
            <span className="text-[13.5px] font-semibold text-ink">{row.desc}</span>
            {figures && <Figure value={figures} size="sm" />}
          </div>
          <p className="mt-[4px] max-w-[560px] text-[12.5px] leading-[1.55] text-sub">{row.note}</p>
        </div>
      );
    },
  },
  {
    key: 'flag',
    header: COPY.colFlag,
    align: 'right',
    width: '130px',
    render: (row) => <StatusPill tone={row.tone} label={row.label} />,
  },
];

function flatten(groups: BoqReviewView['groups']): FlaggedRow[] {
  return groups.flatMap((group) => group.items.map((item) => ({ ...item, group: group.name })));
}

function fill(template: string, values: Record<string, string>): string {
  return Object.entries(values).reduce(
    (text, [key, value]) => text.replaceAll(`{${key}}`, value),
    template
  );
}

export default async function BoqReviewPage({
  params,
  searchParams,
}: {
  params: Promise<{ loanId: string }>;
  searchParams: Promise<{ view?: string }>;
}) {
  const { loanId } = await params;
  const { view: requestedView } = await searchParams;
  // A shared link carrying anything else falls back to the flagged list rather
  // than rendering an empty grid for an unknown filter.
  const view = requestedView === 'all' ? 'all' : 'flagged';

  const [loanResult, boqResult] = await Promise.allSettled([
    apiGet<LoanFacts>(`/api/loans/${encodeURIComponent(loanId)}`),
    apiGet<BoqReviewView>(`/api/loans/${encodeURIComponent(loanId)}/boq/latest`),
  ]);

  if (loanResult.status === 'rejected') {
    // No such loan is a 404 page. Anything else — the backend down, a 500, a
    // refusal — belongs to the error boundary in ../error.tsx, which retries by
    // re-rendering this component. Swallowing it here would show "no loan" for
    // a loan that exists.
    if (loanResult.reason instanceof ApiError && loanResult.reason.status === 404) notFound();
    throw loanResult.reason;
  }
  const loan = loanResult.value;
  const reviseHref = `/owner/loans/${loanId}/boq/revise`;

  if (boqResult.status === 'rejected') {
    if (!(boqResult.reason instanceof ApiError) || boqResult.reason.status !== 404) {
      throw boqResult.reason;
    }
    // The loan is real; its BoQ is not analysed yet. `latest_revision()` and
    // `analysis_for()` both answer 404 for that, and both mean this screen.
    return (
      <div className="flex flex-col gap-5">
        <PageHeader eyebrow={COPY.eyebrow} title={COPY.emptyTitle} />
        <EmptyState
          title={COPY.emptyHeading}
          body={COPY.emptyBody}
          action={
            <Button href="/owner/onboarding" variant="primary">
              {COPY.emptyCta}
            </Button>
          }
        />
      </div>
    );
  }
  const boq = boqResult.value;

  const receivedLabel = boq.received_on ? formatDay(boq.received_on) : null;
  const subParts = [
    boq.contractor,
    receivedLabel && fill(COPY.received, { day: receivedLabel }),
    fill(COPY.checked, { n: String(boq.item_count), locality: loan.locality }),
  ].filter((part): part is string => Boolean(part));

  const shownGroups = view === 'all' ? boq.all_groups : boq.groups;
  const rows = flatten(shownGroups);
  // Counted from the rows, not from the FLAGS RAISED card, because this number
  // heads the table: whatever is listed is what "needs your attention". The two
  // agree on both fixtures. They can diverge — `mappers/boq.py` drops any flag
  // whose `group_name` is outside its hardcoded GROUP_ORDER while the card counts
  // every flag — but that is the mapper silently losing a row, and papering over
  // it here would hide it. Reported to the mapper's owner.
  const flaggedCount = countRows(boq.groups);
  const matchedCount = Math.max(boq.item_count - flaggedCount, 0);
  const otherView = view === 'all' ? 'flagged' : 'all';

  // The schedule is judged once — by the API, whose own DUE BEFORE SLAB card is
  // on this screen — and the pill, the bar and the before-slab figure all read
  // that judgement. One status vocabulary, one verdict.
  const scheduleTone: Tone = paymentTone(boq, STANDARD_PCT_BEFORE_SLAB);
  const afterSlab = amountAfterSlab(boq);
  const gstAmount = gstUpperBound(boq, GST_UPPER_RATE);
  const questionsSent = boq.questions.length > 0 && boq.questions.every((q) => q.status !== 'draft');

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        eyebrow={COPY.eyebrow}
        title={COPY.title}
        sub={subParts.join(' · ')}
        actions={
          <>
            {/* Disabled, and it says why in text: a `title` alone reaches
                neither a keyboard user (a disabled button is out of the tab
                order) nor a screen reader reliably. */}
            <div className="flex flex-col items-start gap-[6px]">
              <Button disabled aria-describedby="pdf-why">
                {COPY.markedUpPdf}
              </Button>
              <p id="pdf-why" className="max-w-[190px] text-[11px] leading-[1.45] text-faint">
                {COPY.pdfWhy}
              </p>
            </div>
            <Button href={reviseHref} className="self-start">
              {COPY.uploadRevised}
            </Button>
            {boq.questions.length > 0 && (
              <SendQuestionsForm
                loanId={boq.loan_id}
                count={boq.questions.length}
                contractor={boq.contractor}
                alreadySent={questionsSent}
                copy={{
                  send: COPY.send,
                  sendAgain: COPY.sendAgain,
                  sending: COPY.sending,
                  sentOne: COPY.sentOne,
                  sentMany: COPY.sentMany,
                  sendNote: COPY.sendNote,
                  withContractor: COPY.withContractor,
                }}
              />
            )}
          </>
        }
      />

      <div className="grid grid-cols-4 gap-3">
        {boq.cards.map((card) => (
          <StatCard
            key={card.label}
            label={card.label}
            value={formatStatValue(card, COPY.countNoun)}
            sub={card.sub}
            tone={card.tone}
          />
        ))}
      </div>

      <div className="flex items-start gap-5">
        <div className="flex min-w-0 flex-1 flex-col gap-[10px]">
          <div className="flex items-center justify-between gap-4">
            <h2 className="text-[14.5px] font-bold text-ink">
              {fill(COPY.attention, {
                flagged: String(flaggedCount),
                total: String(boq.item_count),
              })}
            </h2>
            <SegmentedToggle
              label={COPY.toggleLabel}
              paramName="view"
              value={view}
              options={[
                { value: 'flagged', label: COPY.flagged },
                { value: 'all', label: fill(COPY.all, { n: String(boq.item_count) }) },
              ]}
            />
          </div>

          <CardTable
            columns={COLUMNS}
            rows={rows}
            groupBy={(row) => row.group}
            caption={COPY.tableCaption}
            emptyMessage={COPY.emptyTable}
          />

          <div className="flex items-baseline justify-between gap-4 text-[12.5px] text-faint">
            <span>{fill(COPY.matched, { n: String(matchedCount) })}</span>
            <Link
              href={`/owner/loans/${loanId}/boq?view=${otherView}`}
              scroll={false}
              className="font-semibold text-action hover:underline"
            >
              {view === 'all' ? COPY.showFlagged : COPY.showAll}
            </Link>
          </div>

          {/* The API's `all_groups` is the flagged list until a full BoQ is
              stored (see `mappers/boq.py`). Saying so beats a tab labelled
              "All 40" that quietly shows nine rows. */}
          {view === 'all' && rows.length < boq.item_count && (
            <p className="text-[12px] leading-[1.55] text-faint">
              {fill(COPY.allNote, {
                flagged: String(flaggedCount),
                matched: String(matchedCount),
                locality: loan.locality,
              })}
            </p>
          )}
        </div>

        <StickyRail>
          {boq.payment_schedule.length > 0 && (
            <Panel
              title={COPY.payTitle}
              aside={
                <StatusPill
                  tone={scheduleTone}
                  label={
                    scheduleTone === 'success' ? COPY.standardSchedule : COPY.frontLoaded
                  }
                />
              }
            >
              <p className="text-[12.5px] leading-[1.55] text-sub">
                {fill(COPY.payBody, {
                  pct: formatPct(boq.pct_before_slab),
                  standard: formatPct(STANDARD_PCT_BEFORE_SLAB),
                })}
              </p>
              <PaymentScheduleBar
                stages={boq.payment_schedule}
                tone={scheduleTone}
                copy={{
                  listLabel: COPY.payListLabel,
                  beforeSlab: COPY.beforeSlab,
                  afterSlab: COPY.afterSlab,
                }}
              />
              <div className="mt-[8px] flex items-baseline justify-between gap-3">
                <Figure
                  value={`${COPY.beforeSlab} · ${formatINR(boq.amount_before_slab)}`}
                  tone={scheduleTone}
                  size="sm"
                />
                {afterSlab !== null && (
                  <Figure value={`${COPY.afterSlab} · ${formatINR(afterSlab)}`} size="sm" />
                )}
              </div>
            </Panel>
          )}

          {boq.questions.length > 0 && (
            <Panel
              title={COPY.questionsTitle}
              aside={
                <StatusPill
                  tone={questionsSent ? 'success' : 'neutral'}
                  label={questionsSent ? COPY.questionsSent : COPY.questionsDraft}
                  size="sm"
                />
              }
            >
              <p className="text-[12.5px] leading-[1.5] text-sub">{COPY.questionsBody}</p>
              <div className="mt-[8px]">
                <GuidanceList
                  marker="number"
                  divided
                  items={boq.questions.map((question) => question.text)}
                />
              </div>
              <CopyQuestionsButton
                message={shareMessage({
                  questions: boq.questions,
                  contractor: boq.contractor,
                  receivedLabel,
                })}
                copy={{
                  cta: COPY.copyCta,
                  copied: COPY.copied,
                  manual: COPY.copyManual,
                  manualLabel: COPY.copyManualLabel,
                }}
              />
            </Panel>
          )}

          {!boq.gst_stated && (
            <CalloutBanner
              tone="warn"
              lead={COPY.gstLead}
              body={
                gstAmount === null
                  ? COPY.gstBodyNoAmount
                  : fill(COPY.gstBody, { amount: formatINR(gstAmount) })
              }
            />
          )}
        </StickyRail>
      </div>
    </div>
  );
}
