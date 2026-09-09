// The reading, rendered as the record it is.
//
// Three decisions, all of them about density:
//
// It lives in the main column, not the rail. A 1,600-character credit record in
// a 340px sidebar is a wall of text by construction, whatever it says. The rail
// now holds the decision card alone — the action, sticky, always in reach.
//
// The conclusion comes first. The narrative arrives with its verdict third,
// behind eleven lines of metrics; an officer wants what to do and why, then the
// working. Reordering, never dropping: everything the model wrote is on the
// page, and long figure runs go behind a disclosure that names what it holds.
//
// The verdict line is dropped, because the page header states it in 16px bold
// eight lines above. That is the only content this component removes.
import { FACTS_INLINE_LIMIT, parseRationale, type Block } from './rationale';

/** Prose sits at a readable measure even in a wide column: past ~70 characters
 *  the eye loses the line it is returning to. */
const MEASURE = 'max-w-[68ch]';

export default function RationaleReading({ text }: { text: string }) {
  const blocks = parseRationale(text).filter((block) => block.kind !== 'verdict');
  const conclusion = concludingIndex(blocks);
  const ordered =
    conclusion === -1
      ? blocks
      : [
          // Its heading goes with the move. "Conclusion" above the first
          // paragraph of a panel titled "Why this recommendation" is a label
          // for something the reader can already see.
          ...blocks.slice(conclusion + 1),
          ...blocks.slice(0, conclusion),
        ];

  return (
    <div className="flex flex-col gap-[14px]">
      {ordered.map((block, index) => (
        <Rendered key={index} block={block} lead={index === 0} />
      ))}
    </div>
  );
}

/** Where the conclusion starts, or -1. Matched on the heading the narratives
 *  actually use rather than on position: a rationale that opens with its
 *  verdict is already in the right order and must not be rotated. */
function concludingIndex(blocks: Block[]): number {
  const at = blocks.findIndex(
    (block) => block.kind === 'heading' && /^conclusion|^recommendation/i.test(block.text)
  );
  // Only worth moving if it is genuinely buried.
  return at > 1 ? at : -1;
}

function Rendered({ block, lead }: { block: Block; lead: boolean }) {
  switch (block.kind) {
    case 'heading':
      return (
        <h3 className="text-[12.5px] font-semibold text-ink">{block.text}</h3>
      );

    case 'para':
      return (
        <p
          className={`${MEASURE} ${
            // The first paragraph is the finding. It carries the weight the
            // rest of the column does not.
            lead ? 'text-[14px] leading-[1.6] text-ink' : 'text-[13px] leading-[1.65] text-sub'
          }`}
        >
          {block.text}
        </p>
      );

    case 'facts':
      return block.rows.length > FACTS_INLINE_LIMIT ? (
        <details className="rounded-bank border border-line">
          <summary className="cursor-pointer px-[14px] py-[10px] text-[12.5px] font-semibold text-ink">
            {`The figures behind this — ${block.rows.length} lines`}
          </summary>
          <div className="border-t border-line px-[14px] pb-[10px]">
            <Facts rows={block.rows} />
          </div>
        </details>
      ) : (
        <Facts rows={block.rows} />
      );

    case 'steps':
      return (
        <ol className="flex flex-col gap-[10px]">
          {block.items.map((step) => (
            <li key={step.number} className="flex gap-[10px]">
              <span className="tnum mt-[1px] flex h-[19px] w-[19px] flex-none items-center justify-center rounded-full bg-chip text-[11px] font-semibold text-sub">
                {step.number}
              </span>
              <p className={`${MEASURE} text-[13px] leading-[1.6] text-sub`}>
                {step.title && <b className="font-semibold text-ink">{`${step.title}. `}</b>}
                {step.text}
              </p>
            </li>
          ))}
        </ol>
      );

    default:
      return null;
  }
}

/** Label left, figure right, one hairline between rows. Scannable in a pass,
 *  which a run of "- Label: value" prose is not. */
function Facts({ rows }: { rows: { label: string | null; value: string }[] }) {
  return (
    <dl className="flex flex-col">
      {rows.map((row, index) => (
        <div
          key={index}
          className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-[2px] border-b border-rowline py-[7px] last:border-0"
        >
          {row.label ? (
            <>
              <dt className="text-[12.5px] text-sub">{row.label}</dt>
              {/* tnum, because most of these are money and a column of figures
                  that does not line up is a column nobody reads. */}
              <dd className="tnum max-w-[46ch] text-right text-[12.5px] font-medium text-ink">
                {row.value}
              </dd>
            </>
          ) : (
            <dd className={`${MEASURE} text-[12.5px] leading-[1.55] text-sub`}>{row.value}</dd>
          )}
        </div>
      ))}
    </dl>
  );
}
