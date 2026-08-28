// Change Orders — Neev 6 Change Orders.dc.html.
//
// Scaffolded preview (plan Task 19) with real data behind it: both change orders
// are the ones the seed stores for the golden case, including their "Neev's read"
// text and their tone. The mockup's own three orders are a different set — the
// seed's are the ones the rest of the app can act on, so they win.
//
// What stays a preview is the writing side: replying, accepting and declining
// need a change-order endpoint, which no task in this phase builds, so those
// buttons are disabled and say why.
import CalloutBanner from '@/components/owner/CalloutBanner';
import Panel from '@/components/owner/Panel';
import PreviewEmpty from '@/components/owner/PreviewEmpty';
import { previewLoan } from '@/components/owner/preview';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import CardTable, { type Column } from '@/components/ui/CardTable';
import EmptyState from '@/components/ui/EmptyState';
import Figure from '@/components/ui/Figure';
import KeyValueCard from '@/components/ui/KeyValueCard';
import PageHeader from '@/components/ui/PageHeader';
import StatusPill from '@/components/ui/StatusPill';
import StickyRail from '@/components/ui/StickyRail';
import { formatDelta, formatINR } from '@/lib/format';
import type { Tone } from '@/lib/tone';

const COPY = {
  eyebrow: 'ON EVERY VARIATION',
  title: 'Changes to your contract',
  sub: 'Every change your contractor proposes, priced against the BoQ you signed — visible on paper, not argued from memory.',
  log: '＋ Log a change',
  logWhy: 'Logging a change yourself needs the change-order endpoint, which this preview screen does not have yet.',
  readLead: "Neev's read:",
  counter: 'Reply with counter-rate',
  accept: 'Accept',
  decline: 'Decline',
  actionWhy:
    'Replying to a change order needs the change-order endpoint, which this preview screen does not have yet.',
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
  const loan = previewLoan(loanId);

  const header = (
    <PageHeader
      status={<StatusPill tone="neutral" label="Preview" />}
      eyebrow={COPY.eyebrow}
      title={COPY.title}
      sub={COPY.sub}
      actions={
        <>
          <Button disabled reason={COPY.logWhy} aria-describedby="log-change-why">
            {COPY.log}
          </Button>
        </>
      }
    />
  );

  if (!loan) {
    return (
      <div className="flex flex-col gap-5">
        {header}
        <PreviewEmpty loanId={loanId} what={COPY.emptyWhat} />
      </div>
    );
  }

  // Three states, not two. A declined change is settled but adds nothing to the
  // contract, so it must not be counted with the accepted ones.
  const pending = loan.changeOrders.filter((order) => order.state === 'pending');
  const accepted = loan.changeOrders.filter((order) => order.state === 'accepted');
  const sum = (orders: typeof loan.changeOrders) =>
    orders.reduce((total, order) => total + order.delta, 0);
  const pendingTotal = sum(pending);
  const acceptedTotal = sum(accepted);
  const ifAccepted = loan.boqTotal + acceptedTotal + pendingTotal;
  const overSanction = ifAccepted - loan.sanctioned;
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
          {loan.changeOrders.length === 0 && (
            <EmptyState title={COPY.noneTitle} body={COPY.noneBody} />
          )}

          {loan.changeOrders.map((order) => (
            <Card key={order.id} className="p-[22px]">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-[10px]">
                    <span className="tnum text-[11.5px] text-faint">{order.id}</span>
                    <StatusPill tone={order.tone} label={order.statusLabel} />
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
                      desc: order.signedDesc,
                      amount: order.signedAmount,
                      tone: 'neutral',
                    },
                    {
                      version: 'Now proposed',
                      desc: order.proposedDesc,
                      amount: order.proposedAmount,
                      tone: order.tone,
                    },
                  ]}
                  caption={`${order.title}: the line in your signed BoQ against the line now proposed.`}
                />
              </div>

              <div className="mt-[12px]">
                <CalloutBanner tone={order.tone} lead={COPY.readLead} body={order.neevsRead} />
              </div>

              {order.state === 'pending' && (
                <div className="mt-[14px]">
                  <div className="flex gap-2">
                    <Button
                      variant="primary"
                      disabled
                      reason={COPY.actionWhy}
                      aria-describedby={`${order.id}-why`}
                    >
                      {COPY.counter}
                    </Button>
                    <Button disabled reason={COPY.actionWhy} aria-describedby={`${order.id}-why`}>
                      {COPY.accept}
                    </Button>
                    <Button disabled reason={COPY.actionWhy} aria-describedby={`${order.id}-why`}>
                      {COPY.decline}
                    </Button>
                  </div>
                  <p id={`${order.id}-why`} className="mt-[8px] text-[11.5px] text-faint">
                    {COPY.actionWhy}
                  </p>
                </div>
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
                value: <Figure value={formatINR(loan.boqTotal)} />,
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
