'use client';

// The live half of `Neev 0b Analyzing.dc.html`. The one screen in the product
// that must be a client component: it is an open socket with a picture on it.
//
// WHAT THE MOCKUP DOES NOT SHOW, and what this therefore has to decide:
//
//  * The five phases are NOT the five ADK agents, whatever the handoff README
//    says — they are sub-steps inside `boq_analyst`. So they carry no agent
//    names, and nothing here assumes there are five of them: the count, the
//    names and the order all arrive as `PhaseEvent`s. A phase becomes visible
//    when the run reaches it, because the event contract has no "here is the
//    plan" event to draw the queued tail from. The `queued` styling is
//    implemented anyway — `PhaseEvent.status` has the variant, and the live
//    runner may well emit it.
//  * `ErrorEvent` is published immediately before the terminal `done`. The whole
//    point of that variant is that the redirect must NOT be followed as though
//    the run had succeeded, so a failure latches and the reader is shown what
//    broke and how far it got.
//  * A stream that drops is not a failed run. EventSource reconnects by itself
//    and the backend replays every event the subscriber missed, so a blip shows
//    as "reconnecting" and heals; only repeated failures become an error state.
//  * Landing on this URL after a reload is the ordinary case, not an edge case:
//    the job registry retains its events, so the same subscription replays the
//    run from the beginning. A job the server has never heard of gets a terminal
//    `done` pointing at onboarding, which is why there is no third code path
//    for it here.
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useReducer, useRef, useState } from 'react';
import {
  parsePipelineEvent,
  safeRedirect,
  reduce,
  EMPTY,
  type PhaseEvent,
} from './analyzing-events';
import type { LoanFacts } from './loan-facts';
import Card from '@/components/ui/Card';
import ErrorState from '@/components/ui/ErrorState';
import StatusPill from '@/components/ui/StatusPill';

const COPY = {
  title: 'Reading your contract…',
  /** The mockup reads "40 line items found. Checking each against real Kompally
   *  rates — this takes about a minute." The item count is dropped rather than
   *  hardcoded: at this moment nothing has counted the items in the document
   *  being read, and the count that IS available belongs to the previous
   *  revision. The number the reader wants appears a second later anyway, in the
   *  first phase's own subtitle and in the progress line. */
  leadPrefix: 'Checking each against real ',
  leadSuffix: ' rates — this takes about a minute.',
  docPrefix: 'BoQ — ',
  docFallback: 'Your Bill of Quantities',
  foundHeading: 'FOUND SO FAR',
  foundEmpty: 'Nothing flagged yet. Anything worth your attention appears here as it comes up.',
  waiting: 'Your full report opens when the check finishes',
  skipLead: 'Or skip ahead — ',
  skipLink: 'see the finished report',
  opening: 'Opening your report…',
  reconnecting: 'The connection dropped. Reconnecting — nothing is lost, the check keeps running.',
  connecting: 'Connecting to the check…',
  failedTitle: 'The check stopped early',
  lostTitle: 'We lost the connection',
  lostBody:
    'Your check may still be running on our side. Reconnect to pick it up where it left off.',
  seeSoFar: 'See what we have so far',
};

/** How many failed connection attempts in a row before the screen stops waiting.
 *  EventSource retries roughly every 3s, so this is about ten seconds of silence
 *  — long enough to ride out a backend restart, short enough that a reader is
 *  not left watching a dead socket. */
const MAX_RECONNECTS = 3;

const PHASE_GLYPH: Record<PhaseEvent['status'], string> = {
  done: '✓',
  running: '●',
  queued: '·',
};

const PHASE_LABEL: Record<PhaseEvent['status'], string> = {
  done: 'done',
  running: 'running',
  queued: 'queued',
};

// Token classes, never hex. `done` and `running` deliberately share the success
// tint — that is what the mockup draws — and are told apart by the glyph, the
// pulse and, for anyone the tint does not reach, the status word, which is
// always rendered.
const PHASE_DOT: Record<PhaseEvent['status'], string> = {
  done: 'bg-success-tint text-success',
  running:
    'bg-success-tint text-action animate-[nv-pulse_1.2s_ease-in-out_infinite] motion-reduce:animate-none',
  queued: 'bg-chip text-faint',
};

const PHASE_STATUS_TEXT: Record<PhaseEvent['status'], string> = {
  done: 'text-success',
  running: 'text-action',
  queued: 'text-faint',
};

type Connection = 'connecting' | 'open' | 'retrying' | 'lost';

export default function AnalyzingLive({
  jobId,
  loanId,
  loan,
}: {
  jobId: string;
  loanId: string;
  /** null when the loan record could not be read. The stream is the point of
   *  this screen, so it runs anyway and the header simply says less. */
  loan: LoanFacts | null;
}) {
  const router = useRouter();
  const [state, dispatch] = useReducer(reduce, EMPTY);
  const [connection, setConnection] = useState<Connection>('connecting');
  /** Bumped by the retry button to tear down the old subscription and open a
   *  new one. */
  const [attempt, setAttempt] = useState(0);

  // Read inside the EventSource callbacks, which close over the state they were
  // created with. `ErrorEvent` always precedes the terminal `done` on the same
  // stream, so by the time the `done` branch runs this ref is already set.
  const failedRef = useRef(false);
  const retriesRef = useRef(0);

  useEffect(() => {
    failedRef.current = false;
    retriesRef.current = 0;
    // `connection` is NOT reset here: setState in an effect body cascades a
    // render, and the two ways in are already covered — the initial state is
    // 'connecting', and retry() sets it back before bumping `attempt`.

    const source = new EventSource('/api/jobs/' + encodeURIComponent(jobId) + '/events');
    // Set once the stream has terminated, so the close() below is not mistaken
    // for a dropped connection by the error handler.
    let terminated = false;

    // The run state is cleared on EVERY open, not only the first.
    //
    // `registry.stream()` has no cursor to resume from — it always replays the
    // job's whole event list from the beginning, and neither side speaks
    // `Last-Event-ID`. So an automatic reconnect re-delivers every event already
    // seen. `phase` dedupes by index and `progress` overwrites, but `finding`
    // appends and `FindingEvent` carries no id, so without this a single dropped
    // connection would list every finding twice and a second drop three times.
    // Discarding and refilling from the replay is what makes a blip actually heal.
    //
    // The retry counter is deliberately NOT reset here or on a message: a
    // connection that keeps flapping must eventually reach `lost` and stop, and
    // since a reconnect replays immediately, resetting on either signal would put
    // the ceiling permanently out of reach. Only the reader's own retry clears it.
    source.onopen = () => {
      failedRef.current = false;
      dispatch({ kind: 'reset' });
      setConnection('open');
    };

    source.onmessage = (message: MessageEvent<string>) => {
      const event = parsePipelineEvent(message.data);
      if (event === null) return;
      if (event.type === 'error') failedRef.current = true;
      dispatch({ kind: 'event', event });

      if (event.type === 'done') {
        terminated = true;
        // The server closes after `done` too; closing here first stops
        // EventSource from treating that close as a drop and reconnecting to
        // replay the whole finished run.
        source.close();
        if (failedRef.current) return;
        // A redirect that is not a path on this origin is refused; the reader
        // still lands on their own report rather than nowhere.
        router.replace(safeRedirect(event.redirect) ?? `/owner/loans/${loanId}/boq`);
      }
    };

    source.onerror = () => {
      if (terminated) return;
      retriesRef.current += 1;
      if (source.readyState === EventSource.CLOSED || retriesRef.current > MAX_RECONNECTS) {
        source.close();
        setConnection('lost');
        return;
      }
      setConnection('retrying');
    };

    return () => source.close();
  }, [jobId, loanId, attempt, router]);

  const retry = () => {
    dispatch({ kind: 'reset' });
    setConnection('connecting');
    setAttempt((previous) => previous + 1);
  };

  const documentLabel = loan?.contractor ? COPY.docPrefix + loan.contractor : COPY.docFallback;
  const progress = state.progress;
  const etaSeconds = progress?.eta_s;
  const hasReport = loan !== null && loan.latest_rev !== null;

  return (
    <div className="mx-auto flex max-w-[680px] flex-col">
      <div className="text-center">
        <p className="inline-flex items-center gap-[10px] rounded-pill border border-line bg-card px-4 py-2 shadow-card">
          <span aria-hidden="true" className="text-[15px]">
            📄
          </span>
          <span className="tnum text-[12.5px] text-sub">{documentLabel}</span>
        </p>
        <h1 className="mt-5 font-display text-[26px] font-bold tracking-[-0.02em] text-ink">
          {COPY.title}
        </h1>
        {loan && (
          <p className="mt-2 text-[14px] text-sub">
            {COPY.leadPrefix}
            {loan.locality}
            {COPY.leadSuffix}
          </p>
        )}
      </div>

      <Card className="mt-7 px-6 py-2">
        {state.phases.length === 0 ? (
          <p className="py-[15px] text-[13px] text-faint">{COPY.connecting}</p>
        ) : (
          <ol>
            {state.phases.map((phase) => (
              <li
                key={phase.index}
                aria-current={phase.status === 'running' ? 'step' : undefined}
                className="flex items-center gap-[14px] border-b border-rowline py-[15px]"
              >
                <span
                  aria-hidden="true"
                  className={`flex h-[26px] w-[26px] flex-none items-center justify-center rounded-full text-[13px] ${PHASE_DOT[phase.status]}`}
                >
                  {PHASE_GLYPH[phase.status]}
                </span>
                <span className="min-w-0 flex-1">
                  <span
                    className={`block text-[13.5px] font-semibold ${
                      phase.status === 'queued' ? 'text-faint' : 'text-ink'
                    }`}
                  >
                    {phase.name}
                  </span>
                  {phase.sub && (
                    <span className="mt-[2px] block text-[12px] text-faint">{phase.sub}</span>
                  )}
                </span>
                <span
                  className={`tnum flex-none text-[11.5px] font-semibold ${PHASE_STATUS_TEXT[phase.status]}`}
                >
                  {PHASE_LABEL[phase.status]}
                </span>
              </li>
            ))}
          </ol>
        )}

        <div className="py-[14px]">
          <div
            role="progressbar"
            aria-label={COPY.title}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={progress?.pct}
            className="relative h-[6px] overflow-hidden rounded-[6px] bg-chip"
          >
            <div
              className="absolute inset-y-0 left-0 overflow-hidden rounded-[6px] bg-ink transition-[width] duration-700 ease-out"
              style={{ width: `${progress?.pct ?? 0}%` }}
            >
              <span
                aria-hidden="true"
                className="absolute inset-0 animate-pulse bg-gradient-to-r from-transparent via-bg to-transparent opacity-40 motion-reduce:animate-none"
              />
            </div>
          </div>
          {/* One polite live region for "where the run is", so the progress line
              is announced as it changes instead of silently rewriting itself. */}
          <p
            role="status"
            className="mt-2 flex items-baseline justify-between gap-4 text-[11.5px] text-faint"
          >
            <span>{progress?.detail}</span>
            {typeof etaSeconds === 'number' && etaSeconds > 0 && (
              <span className="tnum flex-none">{`~${etaSeconds}s left`}</span>
            )}
          </p>
        </div>
      </Card>

      <section className="mt-5">
        <h2 className="px-1 text-[12px] font-semibold uppercase tracking-[0.08em] text-faint">
          {COPY.foundHeading}
        </h2>
        {/* Findings arrive one at a time over a socket. Without a live region a
            screen-reader user would never learn that anything had been found. */}
        <ul aria-live="polite" aria-relevant="additions" className="mt-3 flex flex-col gap-[10px]">
          {state.findings.length === 0 ? (
            <li className="px-1 text-[12.5px] text-faint">{COPY.foundEmpty}</li>
          ) : (
            state.findings.map((finding, index) => (
              <li key={`${finding.flag}-${index}`}>
                <Card className="flex items-start gap-3 px-[18px] py-[14px]">
                  <StatusPill tone={finding.tone} label={finding.flag} />
                  <span className="text-[13px] leading-[1.55] text-sub">{finding.text}</span>
                </Card>
              </li>
            ))
          )}
        </ul>

        <div className="mt-6">
          {state.failure !== null ? (
            <>
              <ErrorState
                title={COPY.failedTitle}
                body={state.failure}
                retryHref="/owner/onboarding"
              />
              {state.failureRedirect !== null && (
                <p className="mt-3 text-center text-[12px] text-faint">
                  <Link
                    href={state.failureRedirect}
                    className="font-semibold text-action hover:underline"
                  >
                    {COPY.seeSoFar}
                  </Link>
                </p>
              )}
            </>
          ) : connection === 'lost' ? (
            <ErrorState title={COPY.lostTitle} body={COPY.lostBody} onRetry={retry} />
          ) : (
            <div className="text-center">
              {connection === 'retrying' && (
                <p role="alert" className="mb-3 text-[12.5px] font-semibold text-warn">
                  {COPY.reconnecting}
                </p>
              )}
              <p
                role="status"
                className="inline-block rounded-[10px] bg-chip px-7 py-3 text-[14px] font-semibold text-sub"
              >
                {state.finished ? COPY.opening : COPY.waiting}
              </p>
              {hasReport && !state.finished && (
                <p className="mt-[10px] text-[12px] text-faint">
                  {COPY.skipLead}
                  <Link
                    href={`/owner/loans/${loanId}/boq`}
                    className="font-semibold text-action hover:underline"
                  >
                    {COPY.skipLink}
                  </Link>
                </p>
              )}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
