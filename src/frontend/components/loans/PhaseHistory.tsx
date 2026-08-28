// The history of each build phase — what was claimed, what was seen, what was
// decided — rendered identically for the owner and the lender.
//
// One component with a `skin` prop rather than two trees: the owner's account of
// their own build and the lender's audit trail are the same record, and letting
// them drift apart would be the bug. Only the framing differs, which is a prop.
import Card from '@/components/ui/Card';
import Figure from '@/components/ui/Figure';
import StatusPill from '@/components/ui/StatusPill';
import { formatINR, formatRatio } from '@/lib/format';
import { toneClasses, type Skin } from '@/lib/tone';
import type { PhaseHistoryView } from '@/lib/types';

const COPY = {
  title: 'Every phase, on the record',
  ownerSub:
    'What was claimed at each stage, what the photos showed, and what was released against it.',
  bankSub: 'The full verification and disbursement record for this loan, phase by phase.',
  noEvidence: 'No site photographs were collected for this phase.',
  noEvidenceWhy: 'It was released before Neev was verifying this loan.',
  verified: 'Value in place',
  exposure: 'Exposure then',
  released: 'Released',
  drawn: 'Drawn to date',
  awaiting: 'Awaiting a decision',
  unverified: 'not verified',
};

function longDate(iso: string | null): string {
  if (!iso) return '—';
  const date = new Date(`${iso}T00:00:00`);
  return date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

export default function PhaseHistory({
  phases,
  skin = 'owner',
}: {
  phases: PhaseHistoryView[];
  skin?: Skin;
}) {
  if (phases.length === 0) return null;

  return (
    <section aria-labelledby="phase-history-title">
      <h2 id="phase-history-title" className="text-[14.5px] font-bold text-ink">
        {COPY.title}
      </h2>
      <p className="mt-1 text-[12.5px] text-sub">
        {skin === 'bank' ? COPY.bankSub : COPY.ownerSub}
      </p>

      <ol className="mt-4 flex flex-col gap-3">
        {phases.map((phase) => {
          const exposureTone = phase.exposure !== null && phase.exposure > 1 ? 'danger' : 'success';
          return (
            <li key={phase.tranche_number}>
              <Card skin={skin} className="p-[17px]">
                <div className="flex flex-wrap items-baseline justify-between gap-3">
                  <div className="flex items-center gap-[10px]">
                    <h3 className="text-[13.5px] font-bold uppercase tracking-[0.04em] text-ink">
                      {phase.label}
                    </h3>
                    <span className="tnum text-[11.5px] text-faint">
                      T{phase.tranche_number}
                      {phase.inspected_on ? ` · ${longDate(phase.inspected_on)}` : ''}
                    </span>
                  </div>
                  <StatusPill tone={phase.tone} label={phase.status_label} skin={skin} />
                </div>

                <dl className="mt-3 grid grid-cols-4 gap-x-4 gap-y-2">
                  <Cell label={COPY.released}>
                    <Figure value={formatINR(phase.released_amount)} skin={skin} />
                  </Cell>
                  <Cell label={COPY.drawn}>
                    <Figure value={formatINR(phase.disbursed_cum)} skin={skin} />
                  </Cell>
                  <Cell label={COPY.verified}>
                    <Figure
                      value={
                        phase.verified_value === null
                          ? COPY.unverified
                          : formatINR(phase.verified_value)
                      }
                      skin={skin}
                    />
                  </Cell>
                  <Cell label={COPY.exposure}>
                    <Figure
                      value={formatRatio(phase.exposure)}
                      tone={phase.exposure === null ? 'neutral' : exposureTone}
                      skin={skin}
                    />
                  </Cell>
                </dl>

                {phase.observed_by_neev ? (
                  <div className="mt-[14px] border-t border-line pt-3">
                    <div className="flex flex-wrap gap-[6px]">
                      {phase.photos.flatMap((photo) =>
                        photo.chips.map((chip) => (
                          <StatusPill
                            key={`${photo.slot_key}-${chip.label}`}
                            tone={chip.tone}
                            label={chip.label}
                            skin={skin}
                            size="sm"
                          />
                        ))
                      )}
                    </div>
                    {phase.evidence_notes.length > 0 && (
                      <ul className="mt-2 flex flex-col gap-1">
                        {phase.evidence_notes.map((note) => (
                          <li key={note} className="text-[12px] leading-[1.5] text-sub">
                            {note}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                ) : (
                  // Saying this plainly is the point: an empty evidence grid
                  // would read as missing data rather than as the reason this
                  // loan is where it is.
                  <p
                    className={`mt-[14px] border-t border-line pt-3 text-[12px] leading-[1.5] ${toneClasses('neutral', skin).text}`}
                  >
                    {COPY.noEvidence} <span className="text-faint">{COPY.noEvidenceWhy}</span>
                  </p>
                )}

                {phase.decision ? (
                  <p className="mt-3 text-[12px] text-sub">
                    <StatusPill
                      tone={phase.decision.tone}
                      label={phase.decision.action}
                      skin={skin}
                      size="sm"
                    />{' '}
                    by {phase.decision.decided_by} on {longDate(phase.decision.decided_at)}
                    {phase.decision.note ? ` — ${phase.decision.note}` : ''}
                  </p>
                ) : phase.status === 'on_hold' ? (
                  <p className="mt-3 text-[12px] font-semibold text-danger">
                    {COPY.awaiting}
                    {phase.recommendation ? ` — Neev recommends ${phase.recommendation}` : ''}
                  </p>
                ) : null}
              </Card>
            </li>
          );
        })}
      </ol>
    </section>
  );
}

function Cell({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-[10.5px] font-semibold uppercase tracking-[0.06em] text-faint">
        {label}
      </dt>
      <dd className="mt-[3px]">{children}</dd>
    </div>
  );
}
