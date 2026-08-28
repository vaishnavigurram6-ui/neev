import type { Skin } from '@/lib/tone';

export default function ProfileChip({
  name,
  sub,
  skin,
}: {
  name: string;
  sub: string;
  skin: Skin;
}) {
  const nameClass = skin === 'bank' ? 'text-card' : 'text-ink';
  const subClass = skin === 'bank' ? 'text-bank-inactive' : 'text-faint';
  const avatar = skin === 'bank' ? 'bg-bank-accent text-card' : 'bg-ink text-card';
  const initials = name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase();

  return (
    <div className="flex items-center gap-[10px]">
      <div className="text-right">
        <div className={`text-[13px] font-semibold leading-[1.2] ${nameClass}`}>{name}</div>
        <div className={`text-[11px] ${subClass}`}>{sub}</div>
      </div>
      <div
        className={`flex h-8 w-8 items-center justify-center rounded-full text-[12px] font-semibold ${avatar}`}
        aria-hidden="true"
      >
        {initials}
      </div>
    </div>
  );
}
