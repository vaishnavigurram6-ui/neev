// The shape hiding inside a rationale.
//
// Both narratives arrive as text with real structure in it — a verdict line,
// section headings, runs of "- Label: value", numbered asks for the builder —
// and the screen used to pour the whole thing into one <p> in the 340px rail.
// JSX collapses the newlines, so 1,600 characters of credit record rendered as
// a single wall of prose in the narrowest column on the page. Nothing was
// wrong with the writing; it was being thrown away.
//
// This parses the structure back out so the screen can render it. Pure, and
// unit-tested in tests/rationale.test.mjs: it runs on model output, so it has
// to degrade to plain paragraphs rather than lose a line it does not recognise.

export interface FactRow {
  /** Null for a bullet with no "label:" part — kept as a value rather than
   *  dropped, because a line without a colon is still a line of the record. */
  label: string | null;
  value: string;
}

export interface Step {
  number: string;
  title: string | null;
  text: string;
}

export type Block =
  /** "DISBURSAL RECOMMENDATION: HOLD" — the verdict, which the page header
   *  already states in 16px bold. Returned separately so the reading does not
   *  repeat it three inches below. */
  | { kind: 'verdict'; label: string; value: string }
  | { kind: 'heading'; text: string }
  | { kind: 'para'; text: string }
  | { kind: 'facts'; rows: FactRow[] }
  | { kind: 'steps'; items: Step[] };

/** "1. Key Risk & Financial Metrics:" — a numbered line with nothing after the
 *  colon is a section heading, not an instruction. */
const SECTION = /^(\d+)\.\s+(.+?):\s*$/;
/** "1. Rate Adjustments: Items 2.3 ... realign these rates?" */
const STEP = /^(\d+)\.\s+(?:(.+?):\s+)?(.+)$/;
/** "- Exposure Ratio: 1.11 (…)" */
const BULLET = /^[-•*]\s+(?:(.+?):\s+)?(.+)$/;
/** "DISBURSAL RECOMMENDATION: HOLD" — shouted, and only at the very top. */
const VERDICT = /^([A-Z][A-Z\s&/]{4,40}):\s*(.+)$/;

export function parseRationale(text: string): Block[] {
  const blocks: Block[] = [];
  let facts: FactRow[] | null = null;
  let steps: Step[] | null = null;
  let para: string[] | null = null;

  const flush = () => {
    if (facts) blocks.push({ kind: 'facts', rows: facts });
    if (steps) blocks.push({ kind: 'steps', items: steps });
    if (para) {
      const joined = para.join(' ').trim();
      // A paragraph that ends in a colon is introducing what follows — "Here
      // is a breakdown of where your project stands:" — so it becomes that
      // list's heading rather than a stranded sentence above it.
      if (joined) blocks.push(joined.endsWith(':')
        ? { kind: 'heading', text: joined.slice(0, -1) }
        : { kind: 'para', text: joined });
    }
    facts = steps = para = null;
  };

  for (const raw of text.split('\n')) {
    const line = raw.trim();
    if (!line) {
      flush();
      continue;
    }

    if (blocks.length === 0 && !facts && !steps && !para) {
      const verdict = VERDICT.exec(line);
      if (verdict) {
        blocks.push({ kind: 'verdict', label: verdict[1].trim(), value: verdict[2].trim() });
        continue;
      }
    }

    const section = SECTION.exec(line);
    if (section) {
      flush();
      blocks.push({ kind: 'heading', text: section[2].trim() });
      continue;
    }

    const bullet = BULLET.exec(line);
    if (bullet) {
      if (!facts) flush();
      facts ??= [];
      facts.push({ label: bullet[1]?.trim() ?? null, value: bullet[2].trim() });
      continue;
    }

    const step = STEP.exec(line);
    if (step) {
      if (!steps) flush();
      steps ??= [];
      steps.push({ number: step[1], title: step[2]?.trim() ?? null, text: step[3].trim() });
      continue;
    }

    if (!para) flush();
    para ??= [];
    para.push(line);
  }
  flush();
  return blocks;
}

/** Above this, a run of figures is a table rather than a list — and on the
 *  officer's narrative it is the same table the math panel already shows, so
 *  the screen puts it behind a disclosure instead of on the page twice. Set at
 *  6 so the owner's five-line breakdown stays open. */
export const FACTS_INLINE_LIMIT = 6;
