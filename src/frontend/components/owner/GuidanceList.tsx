// GuidanceList.tsx — the "→ do this next" / "✓ this is settled" / numbered-step
// lists that appear in the rail of four different mockups. They are lists, so
// they are a real <ul>/<ol>: ported literally they would be a stack of divs and
// a screen reader would never announce "list, 3 items".
//
// The marker glyph is decorative and hidden from assistive tech — the list
// semantics already carry the structure, and a spoken "right arrow" before every
// item is noise.

export type Marker = 'arrow' | 'check' | 'number';

const GLYPH: Record<Exclude<Marker, 'number'>, string> = {
  arrow: '→',
  check: '✓',
};

const GLYPH_TONE: Record<Exclude<Marker, 'number'>, string> = {
  arrow: 'text-faint',
  check: 'text-success',
};

export default function GuidanceList({
  items,
  marker = 'arrow',
  divided = false,
}: {
  items: React.ReactNode[];
  marker?: Marker;
  /** Numbered step lists in the mockups have a rule between rows. */
  divided?: boolean;
}) {
  const rowClass = divided
    ? 'flex items-start gap-[10px] border-b border-rowline py-[11px] last:border-0 last:pb-0 first:pt-0'
    : 'flex items-start gap-[10px]';

  if (marker === 'number') {
    return (
      <ol className="flex flex-col">
        {items.map((item, index) => (
          <li key={index} className={rowClass}>
            <span
              aria-hidden="true"
              className="tnum mt-[1px] flex h-[20px] w-[20px] flex-none items-center justify-center rounded-full bg-chip text-[11px] text-sub"
            >
              {index + 1}
            </span>
            <span className="text-[12.5px] leading-[1.55] text-sub">{item}</span>
          </li>
        ))}
      </ol>
    );
  }

  return (
    <ul className={divided ? 'flex flex-col' : 'flex flex-col gap-[10px]'}>
      {items.map((item, index) => (
        <li key={index} className={rowClass}>
          <span aria-hidden="true" className={`flex-none ${GLYPH_TONE[marker]}`}>
            {GLYPH[marker]}
          </span>
          <span className="text-[12.5px] leading-[1.55] text-sub">{item}</span>
        </li>
      ))}
    </ul>
  );
}
