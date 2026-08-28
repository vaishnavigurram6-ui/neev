// Figure.tsx — every number, id and ratio in the product renders through this.
// The handoff makes mono numerals a hard rule; centralising it means no screen
// has to remember.
import { toneClasses, type Skin, type Tone } from '@/lib/tone';

export default function Figure({
  value,
  tone = 'neutral',
  skin = 'owner',
  size = 'md',
}: {
  value: string;
  tone?: Tone;
  skin?: Skin;
  size?: 'sm' | 'md' | 'lg';
}) {
  const { text } = toneClasses(tone, skin);
  const dims =
    size === 'lg'
      ? 'text-[23px] font-semibold'
      : size === 'sm'
        ? 'text-[12px] font-medium'
        : 'text-[13.5px] font-medium';
  return <span className={`tnum ${dims} ${text}`}>{value}</span>;
}
