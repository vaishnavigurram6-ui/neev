// Revised Contract — Neev 1b Revised Contract.dc.html.
//
// Scaffolded preview (plan Task 19). The diff itself is the one block on any of
// these seven screens with no fixture behind it: the seed stores a single
// revision for the golden case, so revision 2 — the "your contractor answered"
// story the mockup tells — is the mockup's own list, carried in
// `components/owner/preview.ts` and labelled Preview.
//
// A revision with nothing to diff against (revision 1, the contract as first
// received) gets the empty state rather than an invented comparison.
import Link from 'next/link';
import { notFound } from 'next/navigation';
import CalloutBanner from '@/components/owner/CalloutBanner';
import GuidanceList from '@/components/owner/GuidanceList';
import Panel from '@/components/owner/Panel';
import { formatDay, previewLoan, previewRevision, type PreviewFix } from '@/components/owner/preview';
import Button from '@/components/ui/Button';
import CardTable, { type Column } from '@/components/ui/CardTable';
import EmptyState from '@/components/ui/EmptyState';
import Figure from '@/components/ui/Figure';
import KeyValueCard from '@/components/ui/KeyValueCard';
import PageHeader from '@/components/ui/PageHeader';
import StatusPill from '@/components/ui/StatusPill';
import StickyRail from '@/components/ui/StickyRail';
import { formatDelta, formatINR } from '@/lib/format';

const COPY = {
  title: 'Your contractor answered. It checks out.',
  clearedLead: 'this revision is signable.',
  clearedBody:
    'Rates within benchmarks · full scope · everything specified in writing · sane payment schedule · GST stated',
  clearedCta: 'Next: check it against your loan →',
  changedTitle: 'What changed, flag by flag',
  costsTitle: 'What the revision costs you',
  quotedLabel: 'as quoted',
  extrasLabel: 'with the hidden extras',
  beforeTitle: 'Before you sign',
  beforeOne:
    "Keep the revised BoQ and the written replies together — they're your contract now.",
  beforeTwo:
    'The new payment schedule (25% before slab) is what your bank will release against.',
  beforeThreeLead: 'Next: ',
  beforeThreeTail: ' before drawdown.',
  download: 'Download sign-ready BoQ',
  downloadWhy: 'Generating a sign-ready document is out of scope for this build (spec §10).',
  noDiffTitle: 'This is the contract you started with',
  noDiffEmptyTitle: 'Nothing to compare against yet',
  noDiffBody:
    'Revision 1 is the BoQ as first received, so there is nothing yet to compare it against. Its full review — every flag, line by line — is on your contract page.',
  noDiffAction: 'See the review of this revision',
};

const FIX_COLUMNS: Column<PreviewFix>[] = [
  {
    key: 'was',
    header: 'Was',
    width: '130px',
    render: (row) => <StatusPill tone="neutral" label={row.was} />,
  },
  {
    key: 'fix',
    header: 'What changed',
    render: (row) => (
      <div>
        <div className="text-[13.5px] font-semibold text-ink">{row.title}</div>
        <div className="mt-[3px] text-[12.5px] leading-[1.55] text-sub">{row.detail}</div>
      </div>
    ),
  },
  {
    key: 'delta',
    header: 'Effect on the total',
    align: 'right',
    width: '150px',
    render: (row) => (
      <Figure
        value={row.delta === null ? (row.deltaLabel ?? '—') : formatDelta(row.delta)}
        tone={row.tone}
      />
    ),
  },
];

export default async function RevisedContractPage({
  params,
}: {
  params: Promise<{ loanId: string; rev: string }>;
}) {
  const { loanId, rev: revParam } = await params;
  const rev = Number.parseInt(revParam, 10);
  if (!Number.isInteger(rev) || rev < 1) notFound();

  const loan = previewLoan(loanId);
  if (!loan) notFound();

  const revision = previewRevision(loan, rev);
  const boqHref = `/owner/loans/${loanId}/boq`;
  const sanctionHref = `/owner/loans/${loanId}/sanction`;

  // Every revision is reachable: the first one is the review page itself, later
  // ones are this route. No tab is a dead end and none points at a fragment.
  const tabs = [
    { rev: loan.rev, label: `Rev ${loan.rev} · ${loan.flagCount} flags`, href: boqHref },
    ...loan.revisions.map((entry) => ({
      rev: entry.rev,
      label: `Rev ${entry.rev} · ${
        entry.rev === rev ? 'current' : `${entry.flagsResolved} flags resolved`
      }`,
      href: `/owner/loans/${loanId}/boq/rev/${entry.rev}`,
    })),
  ];

  const header = (
    <PageHeader
      eyebrow={`BEFORE SIGNING · REVISION ${rev}`}
      title={revision ? COPY.title : COPY.noDiffTitle}
      sub={
        revision
          ? `Revision ${revision.rev} · received ${formatDay(
              revision.receivedOn
            )} · every line re-checked against the same ${loan.locality} benchmarks`
          : undefined
      }
      actions={
        <>
          <StatusPill tone="neutral" label="Preview" />
          <nav
            aria-label="Contract revisions"
            className="inline-flex flex-none items-center gap-1 rounded-pill bg-chip p-1"
          >
            {tabs.map((tab) =>
              tab.rev === rev ? (
                <span
                  key={tab.rev}
                  aria-current="page"
                  className="rounded-pill bg-card px-[13px] py-[6px] text-[12.5px] font-semibold text-ink shadow-card"
                >
                  {tab.label}
                </span>
              ) : (
                <Link
                  key={tab.rev}
                  href={tab.href}
                  className="rounded-pill px-[13px] py-[6px] text-[12.5px] font-semibold text-sub hover:text-ink"
                >
                  {tab.label}
                </Link>
              )
            )}
          </nav>
        </>
      }
    />
  );

  if (!revision) {
    return (
      <div className="flex flex-col gap-5">
        {header}
        <EmptyState
          title={COPY.noDiffEmptyTitle}
          body={COPY.noDiffBody}
          action={
            <Button href={boqHref} variant="primary">
              {COPY.noDiffAction}
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-5">
      {header}

      <CalloutBanner
        tone="success"
        lead={`All ${revision.flagsResolved} flags resolved — ${COPY.clearedLead}`}
        body={COPY.clearedBody}
        action={
          <Button href={sanctionHref} variant="primary">
            {COPY.clearedCta}
          </Button>
        }
      />

      <div className="flex items-start gap-5">
        <div className="flex min-w-0 flex-1 flex-col gap-[10px]">
          <h2 className="text-[14.5px] font-bold text-ink">{COPY.changedTitle}</h2>
          <CardTable
            columns={FIX_COLUMNS}
            rows={revision.fixes}
            caption="Each flag from the previous revision, what the contractor changed, and what it does to the total."
          />
        </div>

        <StickyRail>
          <KeyValueCard
            title={COPY.costsTitle}
            rows={[
              {
                label: `Rev ${loan.rev}, ${COPY.quotedLabel}`,
                value: <Figure value={formatINR(revision.quotedBefore)} />,
              },
              {
                label: `Rev ${loan.rev}, ${COPY.extrasLabel}`,
                value: (
                  <Figure
                    value={`≈ ${formatINR(revision.quotedBeforeWithExtras)}`}
                    tone="danger"
                  />
                ),
              },
            ]}
            footer={
              <>
                <div className="flex items-baseline justify-between gap-3">
                  <span className="text-[13px] font-semibold text-ink">
                    {`Rev ${revision.rev}, everything on paper`}
                  </span>
                  <Figure value={formatINR(revision.total)} tone="success" size="lg" />
                </div>
                <p className="mt-[10px] text-[12px] leading-[1.65] text-faint">
                  {`${formatINR(revision.coverPageDelta)} more on the cover page — ${formatINR(
                    revision.savedAgainstExtras
                  )} less than where Rev ${loan.rev} was actually heading. Honest numbers cost less.`}
                </p>
              </>
            }
          />

          <Panel title={COPY.beforeTitle}>
            <GuidanceList
              marker="check"
              items={[
                COPY.beforeOne,
                COPY.beforeTwo,
                <span key="sanction">
                  {COPY.beforeThreeLead}
                  <Link href={sanctionHref} className="font-semibold text-action hover:underline">
                    {`check the ${formatINR(revision.total)} against your ${formatINR(
                      loan.sanctioned
                    )} sanction`}
                  </Link>
                  {COPY.beforeThreeTail}
                </span>,
              ]}
            />
            <div className="mt-[16px]">
              <Button disabled title={COPY.downloadWhy} className="w-full">
                {COPY.download}
              </Button>
            </div>
          </Panel>
        </StickyRail>
      </div>
    </div>
  );
}
