import type { Skin } from '@/lib/tone';

// Path taken verbatim from the prototypes' inline SVG.
const HOUSE = 'M20 6 L34 18 L31 18 L31 30 L9 30 L9 18 L6 18 Z';

export default function Logo({
  size = 24,
  skin = 'owner',
  withWordmark = true,
}: {
  size?: number;
  skin?: Skin;
  withWordmark?: boolean;
}) {
  const squareClass = skin === 'bank' ? 'bg-card' : 'bg-brick';
  const glyphClass = skin === 'bank' ? 'fill-bank-bar' : 'fill-card';
  const wordClass = skin === 'bank' ? 'text-card' : 'text-ink';

  return (
    <span className="flex items-center gap-[9px]">
      <span
        className={`flex items-center justify-center rounded-lg ${squareClass}`}
        style={{ width: size, height: size }}
        aria-hidden="true"
      >
        <svg width={size * 0.62} height={size * 0.62} viewBox="0 0 40 40">
          <path d={HOUSE} className={glyphClass} />
        </svg>
      </span>
      {withWordmark && (
        <span className={`font-display text-[17px] font-bold ${wordClass}`}>Neev</span>
      )}
    </span>
  );
}
