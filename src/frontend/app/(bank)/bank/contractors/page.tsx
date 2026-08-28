// Contractor Scorecard — Neev 5 Contractor Scorecard.dc.html.
//
// Scaffolded preview (plan Task 19) over real data: the three firms, their four
// metrics and their tiers are the seed's `CONTRACTORS`. `skin="bank"` is a prop
// on the shared kit, not a parallel component tree, and the dark chrome comes
// from the (bank) group layout.
//
// Two fragment artifacts in the mockup are corrected here per spec §6.1a: the
// nav is the full bank nav including Setup (this file's nav comes from the group
// layout, which already does that), and the row of six hand-coloured columns is a
// real <table> — the figures are a grid and a screen reader has to be able to
// read across a row.
// `Panel` is skin-aware (it is `Card` plus a heading), so both consoles share the
// one composition rather than each keeping a near-identical copy. It lives under
// components/owner/ only because that is where it was first needed.
import { contractorScorecard, type ContractorRow } from '@/components/bank/preview';
import Panel from '@/components/owner/Panel';
import Card from '@/components/ui/Card';
import CardTable, { type Column } from '@/components/ui/CardTable';
import EmptyState from '@/components/ui/EmptyState';
import Figure from '@/components/ui/Figure';
import PageHeader from '@/components/ui/PageHeader';
import StatusPill from '@/components/ui/StatusPill';
import { formatPct, formatQty } from '@/lib/format';

const COPY = {
  eyebrow: 'CONTRACTOR SCORECARD',
  title: 'The builders behind the book',
  sub: 'A credit signal on contractors, not borrowers — accumulated from every BoQ parsed and every site verified. No lender holds this today.',
  note: 'illustrative · compounds with every loan',
  compoundsTitle: 'Why this compounds',
  compoundsBody:
    'The same local contractors appear across dozens of loans. After a few hundred, this becomes a private credit signal on builders that no Indian lender holds for small contractors — and it gets sharper with every BoQ parsed.',
  tiersTitle: 'How the tiers are set',
  tiersBody:
    'Derived only from per-loan pipeline outputs: flags per BoQ parsed, share of under-specified lines, verified overrun against original BoQ, and inter-tranche site inactivity. No manual ratings.',
  emptyTitle: 'No contractors on the book yet',
  emptyBody:
    'Contractor scores accumulate from the BoQs and site verifications on your loans. Add loans in Setup and the scorecard fills itself.',
};

const COLUMNS: Column<ContractorRow>[] = [
  {
    key: 'name',
    header: 'Contractor',
    render: (row) => (
      <div>
        <div className="text-[14px] font-bold text-ink">{row.name}</div>
        <div className="mt-[3px] text-[12px] text-faint">
          {`${row.sites} ${row.sites === 1 ? 'loan' : 'loans'} on the book`}
        </div>
      </div>
    ),
  },
  {
    key: 'flags',
    header: 'Flags / BoQ',
    align: 'right',
    width: '120px',
    render: (row) => (
      <Figure value={formatQty(row.flagsPerBoq)} tone={row.metricTones.flags} skin="bank" />
    ),
  },
  {
    key: 'underspecified',
    header: 'Under-specified',
    align: 'right',
    width: '140px',
    render: (row) => (
      <Figure
        value={formatPct(row.underspecifiedShare)}
        tone={row.metricTones.underspecified}
        skin="bank"
      />
    ),
  },
  {
    key: 'overrun',
    header: 'Budget overrun',
    align: 'right',
    width: '140px',
    render: (row) => (
      <Figure
        value={`+${formatPct(row.overrunPct)} avg`}
        tone={row.metricTones.overrun}
        skin="bank"
      />
    ),
  },
  {
    key: 'quiet',
    header: 'Sites gone quiet',
    align: 'right',
    width: '140px',
    render: (row) => (
      <Figure
        value={`${row.sitesGoneQuiet} ${row.sitesGoneQuiet === 1 ? 'site' : 'sites'}`}
        tone={row.metricTones.quiet}
        skin="bank"
      />
    ),
  },
  {
    key: 'tier',
    header: 'Tier',
    align: 'right',
    width: '120px',
    render: (row) => <StatusPill tone={row.tone} label={row.tier} skin="bank" />,
  },
];

export default function ContractorScorecardPage() {
  const rows = contractorScorecard();

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        eyebrow={COPY.eyebrow}
        title={COPY.title}
        sub={COPY.sub}
        actions={
          <>
            <StatusPill tone="neutral" label="Preview" skin="bank" />
            <span className="tnum self-center text-[11.5px] text-faint">{COPY.note}</span>
          </>
        }
      />

      {rows.length === 0 ? (
        <EmptyState title={COPY.emptyTitle} body={COPY.emptyBody} />
      ) : (
        <CardTable
          columns={COLUMNS}
          rows={rows}
          skin="bank"
          caption="Every contractor on the book, their four risk metrics, and the tier those metrics put them in."
        />
      )}

      <div className="grid grid-cols-2 gap-4">
        <Card skin="bank" className="bg-bank-bar p-[22px]">
          <h2 className="text-[14px] font-bold text-bank-surface">{COPY.compoundsTitle}</h2>
          <p className="mt-2 text-[13px] leading-[1.65] text-bank-inactive">
            {COPY.compoundsBody}
          </p>
        </Card>
        <Panel title={COPY.tiersTitle} skin="bank">
          <p className="text-[13px] leading-[1.65] text-sub">{COPY.tiersBody}</p>
        </Panel>
      </div>
    </div>
  );
}
