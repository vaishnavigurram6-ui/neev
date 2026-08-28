import { toneClasses, type Skin, type Tone } from '@/lib/tone';

// The most repeated atom in the bundle — 10+ files, six vocabularies. The label
// is always rendered, never replaced by colour: status must survive for someone
// who cannot distinguish the red tint.
export default function StatusPill({
  tone,
  label,
  skin = 'owner',
  size = 'md',
}: {
  tone: Tone;
  label: string;
  skin?: Skin;
  size?: 'sm' | 'md';
}) {
  const { pill } = toneClasses(tone, skin);
  const radius = skin === 'bank' ? 'rounded-[6px]' : 'rounded-full';
  const dims = size === 'sm' ? 'px-2 py-[2px] text-[10.5px]' : 'px-[9px] py-[3px] text-[11px]';
  return (
    <span
      className={`inline-flex flex-none items-center whitespace-nowrap font-semibold ${radius} ${dims} ${pill}`}
    >
      {label}
    </span>
  );
}
