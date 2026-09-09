// Change Orders — Neev 6 Change Orders.dc.html.
//
// Live against `GET /api/loans/{id}/change-orders`, and the writing side works:
// accept, decline and counter all POST to the reply endpoint, and an owner can
// log a change their contractor asked for verbally. The running total in the
// rail comes from the mapper rather than being re-added here, so the rows and
// the figure the owner decides against can never disagree.
//
// Was a scaffolded preview (plan Task 19) reading a transcription of the seed.
import CalloutBanner from '@/components/owner/CalloutBanner';
import Panel from '@/components/owner/Panel';
import Card from '@/components/ui/Card';
import CardTable, { type Column } from '@/components/ui/CardTable';
import EmptyState from '@/components/ui/EmptyState';
import Figure from '@/components/ui/Figure';
import KeyValueCard from '@/components/ui/KeyValueCard';
import PageHeader from '@/components/ui/PageHeader';
import StatusPill from '@/components/ui/StatusPill';
import StickyRail from '@/components/ui/StickyRail';
import { ApiError, apiGet } from '@/lib/api';
import { formatDelta, formatINR } from '@/lib/format';
import type { Tone } from '@/lib/tone';
import type { ChangeOrdersView } from '@/lib/types';
import LogChange from './LogChange';
import ReplyCard from './ReplyCard';

const COPY = {
  eyebrow: 'ON EVERY VARIATION',
  title: 'Changes to your contract',
  sub: 'Every change your contractor proposes, priced against the BoQ you signed — visible on paper, not argued from memory.',
  log: '＋ Log a change',
  logTitle: 'Log a change your contractor asked for',
  logLead:
    'Asked for verbally, or on the phone? Write it down here and it is on the record — priced against the line you signed, like every other change.',
  readLead: "Neev's read:",
  counter: 'Send counter',
  counterLabel: 'Counter at (₹)',
  accept: 'Accept',
  decline: 'Decline',
  unreachableTitle: 'We could not load your changes',
  unreachable:
    'The service that holds your change orders did not answer. Reload the page in a moment — nothing has been lost.',
  totalTitle: 'Running total',
  signedLabel: 'Contract you signed',
  acceptedLabel: 'Changes accepted',
  pendingLabel: 'Awaiting your reply',
  ifAcceptedLabel: 'If accepted as proposed',
  overLead: "That's ",
  overTailOne: ' over your sanction. Counter the pending change before accepting.',
  overTailMany: ' over your sanction. Counter the pending changes before accepting.',
  overTailNone:
    ' over your sanction on the changes already accepted. Talk to your lender before the next one.',
  withinTail: ' inside your sanction, even if every pending change is accepted as proposed.',
  whyTitle: 'Why this page matters',
  whyBody:
    'Margin trimmed from a low headline quote is usually recovered here, change by change. Pricing each one against the signed BoQ keeps that visible — and gives you the paper trail if a dispute comes.',
  noneTitle: 'No changes to your contract yet',
  noneBody:
    'When your contractor proposes a variation, it lands here priced against the BoQ you signed — so you can see what it costs before you agree to it.',
  emptyWhat: 'This is where every change your contractor proposes would be priced and listed.',
};

/** The stored status, in the owner's words. One vocabulary, resolved once. */
const STATUS_LABEL: Record<string, string> = {
  pending: 'Awaiting your reply',
  countered: 'You countered',
  accepted: 'Accepted',
  declined: 'Declined',
};

const SETTLED_LINE: Record<string, string> = {
  accepted: 'You accepted this change, so it is part of your contract total.',
  declined: 'You declined this change. The line you signed stands.',
};

interface ComparisonRow {
  version: string;
  desc: string;
  amount: number;
  tone: Tone;
}

const COMPARISON_COLUMNS: Column<ComparisonRow>[] = [
  {
    key: 'version',
    header: 'Version',
    width: '190px',
    render: (row) => (
      <span className="text-[10.5px] font-semibold uppercase tracking-[0.06em] text-faint">
        {row.version}
      </span>
    ),
  },
  {
    key: 'desc',
    header: 'The line as written',
    render: (row) => <span className="text-[12.5px] leading-[1.5] text-sub">{row.desc}</span>,
  },
  {
    key: 'amount',
    header: 'Amount',
    align: 'right',
    width: '140px',
    render: (row) => <Figure value={formatINR(row.amount)} tone={row.tone} />,
  },
];

export default async function ChangeOrdersPage({
  params,
}: {
  params: Promise<{ loanId: string }>;
}) {
  const { loanId } = await params;

  let view: ChangeOrdersView | null = null;
  let unreachable = false;
  try {
    view = await apiGet<ChangeOrdersView>(`/api/loans/${loanId}/change-orders`);
  } catch (cause) {
    // A loan with no BoQ yet has no signed total to price changes against, and
    // that is a "nothing here yet", not a failure. Anything else is.
    if (!(cause instanceof ApiError)) throw cause;
    if (cause.status !== 404) unreachable = true;
  }

  const header = (
    <PageHeader
      eyebrow={COPY.eyebrow}
      title={COPY.title}
      sub={COPY.sub}
      actions={<LogChange loanId={loanId} copy={{ cta: COPY.log, title: COPY.logTitle, lead: COPY.logLead }} />}
    />
  );

  if (view === null) {
    return (
      <div className="flex flex-col gap-5">
        {header}
        <EmptyState
          title={unreachable ? COPY.unreachableTitle : COPY.noneTitle}
          body={unreachable ? COPY.unreachable : COPY.emptyWhat}
        />
      </div>
    );
  }

  // Every figure below comes from the mapper. Re-adding them here is how a
  // screen ends up disagreeing with its own rows: three states, not two, and a
  // countered order is priced at the counter rather than at the proposal.
  const orders = view.orders;
  const pending = orders.filter((order) => order.open);
  const accepted = orders.filter((order) => order.status === 'accepted');
  const { accepted_total: acceptedTotal, pending_total: pendingTotal } = view;
  const ifAccepted = view.if_accepted_total;
  const overSanction = view.over_sanction;
  const overTone = overSanction > 0 ? 'danger' : 'success';
  const overTail =
    overSanction <= 0
      ? COPY.withinTail
      : pending.length === 0
        ? COPY.overTailNone
        : pending.length === 1
          ? COPY.overTailOne
          : COPY.overTailMany;

  return (
    <div className="flex flex-col gap-5">
      {header}

      <div className="flex items-start gap-5">
        <div className="flex min-w-0 flex-1 flex-col gap-[14px]">
          {orders.length === 0 && <EmptyState title={COPY.noneTitle} body={COPY.noneBody} />}

          {orders.map((order) => (
            <Card key={order.id} className="p-[22px]">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-[10px]">
                    <span className="tnum text-[11.5px] text-faint">CO-{order.id}</span>
                    <StatusPill tone={order.tone} label={STATUS_LABEL[order.status] ?? order.status} />
                  </div>
                  <h2 className="mt-2 text-[15px] font-bold text-ink">{order.title}</h2>
                </div>
                <Figure value={formatDelta(order.delta)} tone={order.tone} size="lg" />
              </div>

              <div className="mt-[14px]">
                <CardTable
                  columns={COMPARISON_COLUMNS}
                  rows={[
                    {
                      version: 'In your signed BoQ',
                      desc: order.signed_desc,
                      amount: order.signed_amount,
                      tone: 'neutral',
                    },
                    {
                      version: 'Now proposed',
                      desc: order.proposed_desc,
                      amount: order.proposed_amount,
                      tone: order.tone,
                    },
                  ]}
                  caption={`${order.title}: the line in your signed BoQ against the line now proposed.`}
                />
              </div>

              <div className="mt-[12px]">
                <CalloutBanner tone={order.tone} lead={COPY.readLead} body={order.neevs_read} />
              </div>

              {order.open ? (
                <ReplyCard
                  loanId={loanId}
                  changeOrderId={order.id}
                  proposedAmount={order.counter_amount ?? order.proposed_amount}
                  signedAmount={order.signed_amount}
                  labels={{
                    counter: COPY.counter,
                    counterLabel: COPY.counterLabel,
                    accept: COPY.accept,
                    decline: COPY.decline,
                  }}
                />
              ) : (
                <p className="mt-[12px] text-[12px] text-faint">
                  {SETTLED_LINE[order.status] ?? ''}
                  {order.owner_note ? ` “${order.owner_note}”` : ''}
                </p>
              )}
            </Card>
          ))}
        </div>

        <StickyRail>
          <KeyValueCard
            title={COPY.totalTitle}
            rows={[
              {
                label: COPY.signedLabel,
                value: <Figure value={formatINR(view.signed_total)} />,
              },
              {
                label: `${COPY.acceptedLabel} (${accepted.length})`,
                value: <Figure value={formatDelta(acceptedTotal)} />,
              },
              {
                label: `${COPY.pendingLabel} (${pending.length})`,
                value: <Figure value={formatDelta(pendingTotal)} tone="danger" />,
              },
            ]}
            footer={
              <>
                <div className="flex items-baseline justify-between gap-3">
                  <span className="text-[13px] font-semibold text-ink">
                    {COPY.ifAcceptedLabel}
                  </span>
                  <Figure value={formatINR(ifAccepted)} tone={overTone} size="lg" />
                </div>
                <p className="mt-[10px] text-[12px] leading-[1.6] text-faint">
                  {COPY.overLead}
                  <Figure value={formatINR(Math.abs(overSanction))} size="sm" tone={overTone} />
                  {overTail}
                </p>
              </>
            }
          />

          <Panel title={COPY.whyTitle}>
            <p className="text-[12.5px] leading-[1.65] text-sub">{COPY.whyBody}</p>
          </Panel>
        </StickyRail>
      </div>
    </div>
  );
}
