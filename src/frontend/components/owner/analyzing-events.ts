// The SSE event contract, client side. Mirrors `src/backend/app/schemas/events.py`
// field for field.
//
// Two of the five variants are renamed here — `ProgressEvent` and `ErrorEvent`
// are both DOM globals, and a module-local interface of the same name shadows
// the global for the whole file, which is exactly the kind of quiet collision
// that makes an `addEventListener` handler typecheck against the wrong shape.
// `Run*` prefixes keep them distinct; the `type` discriminants are unchanged, so
// the wire format is identical.
//
// Nothing here is generated: `lib/api-types.ts` comes from the OpenAPI document,
// and the SSE stream has no schema in it — the endpoint's response body is
// `text/event-stream`, so the event union is invisible to OpenAPI. Hand-written
// is the only option, which is why `parsePipelineEvent` validates rather than
// casting.

import type { Tone } from '@/lib/tone';

export interface PhaseEvent {
  type: 'phase';
  index: number;
  status: 'done' | 'running' | 'queued';
  name: string;
  sub: string | null;
}

export interface FindingEvent {
  type: 'finding';
  flag: string;
  tone: Tone;
  text: string;
}

/** `ProgressEvent` on the backend. */
export interface RunProgressEvent {
  type: 'progress';
  pct: number;
  detail: string;
  eta_s: number | null;
}

/** `ErrorEvent` on the backend — added in the Task 12 wave.
 *
 *  It is published immediately BEFORE the terminal `done`, never instead of it,
 *  so the stream still ends the same way. A consumer that ignores it follows the
 *  redirect as though the run had succeeded; that is the bug it exists to fix,
 *  so the Analyzing screen must not ignore it. */
export interface RunErrorEvent {
  type: 'error';
  message: string;
  redirect: string | null;
}

export interface DoneEvent {
  type: 'done';
  redirect: string;
}

export type PipelineEvent =
  | PhaseEvent
  | FindingEvent
  | RunProgressEvent
  | RunErrorEvent
  | DoneEvent;

const TONES: readonly Tone[] = ['danger', 'warn', 'success', 'neutral'];
const PHASE_STATUSES: readonly PhaseEvent['status'][] = ['done', 'running', 'queued'];

function str(value: unknown): string | null {
  return typeof value === 'string' ? value : null;
}

function int(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

/** Parses one `data:` frame, or returns null.
 *
 *  Returning null rather than throwing is deliberate: a frame this build does not
 *  understand — a variant added to the union later, or a truncated line — must
 *  not take the screen to its error boundary mid-run. An unparseable frame is
 *  skipped and the stream keeps going, which is the same forwards-compatibility
 *  the backend built ErrorEvent to have. */
export function parsePipelineEvent(raw: string): PipelineEvent | null {
  let value: unknown;
  try {
    value = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof value !== 'object' || value === null) return null;
  const data = value as Record<string, unknown>;

  switch (data.type) {
    case 'phase': {
      const index = int(data.index);
      const name = str(data.name);
      const status = PHASE_STATUSES.find((candidate) => candidate === data.status);
      if (index === null || name === null || status === undefined) return null;
      return { type: 'phase', index, status, name, sub: str(data.sub) };
    }
    case 'finding': {
      const flag = str(data.flag);
      const text = str(data.text);
      if (flag === null || text === null) return null;
      // An unknown tone degrades to neutral rather than dropping the finding:
      // the words carry the meaning, and a finding the owner never sees is a
      // worse failure than one shown in the wrong tint.
      const tone = TONES.find((candidate) => candidate === data.tone) ?? 'neutral';
      return { type: 'finding', flag, tone, text };
    }
    case 'progress': {
      const pct = int(data.pct);
      const detail = str(data.detail);
      if (pct === null || detail === null) return null;
      return { type: 'progress', pct, detail, eta_s: int(data.eta_s) };
    }
    case 'error': {
      const message = str(data.message);
      if (message === null) return null;
      return { type: 'error', message, redirect: str(data.redirect) };
    }
    case 'done': {
      const redirect = str(data.redirect);
      if (redirect === null) return null;
      return { type: 'done', redirect };
    }
    default:
      return null;
  }
}

/** Where a `done` or `error` redirect may send the reader.
 *
 *  The redirect arrives over the network, so it is untrusted input even though
 *  the backend composes it: `router.replace()` will happily follow
 *  `//evil.example`, which a browser reads as a protocol-relative URL rather
 *  than a path. Same-origin absolute paths only; anything else is refused and
 *  the caller falls back to a route it chose itself. */
export function safeRedirect(target: string | null): string | null {
  if (target === null) return null;
  return /^\/(?![\\/])/.test(target) ? target : null;
}
