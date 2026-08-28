// StageStrip.tsx — the 5-stage checklist (Tranche Decision) and the journey
// strip (Onboarding, Login) are the same shape.
import { toneClasses, type Skin } from '@/lib/tone';

export interface Stage {
  name: string;
  sub: string;
  state: 'done' | 'current' | 'todo';
}

export default function StageStrip({
  stages,
  skin = 'owner',
}: {
  stages: Stage[];
  skin?: Skin;
}) {
  return (
    <ol className="flex gap-[10px]">
      {stages.map((stage) => {
        const tone = stage.state === 'todo' ? 'neutral' : 'success';
        const { bg, text } = toneClasses(tone, skin);
        const radius = skin === 'bank' ? 'rounded-bank' : 'rounded-card';
        return (
          <li
            key={stage.name}
            className={`flex-1 border border-line px-3 py-[10px] ${radius} ${stage.state === 'todo' ? 'bg-card' : bg}`}
          >
            <div className="flex items-center gap-2">
              <span
                className={`flex h-[18px] w-[18px] items-center justify-center rounded-full text-[11px] font-bold ${stage.state === 'todo' ? 'bg-chip text-faint' : `${bg} ${text}`}`}
                aria-hidden="true"
              >
                {stage.state === 'todo' ? '·' : '✓'}
              </span>
              <span
                className={`text-[12.5px] font-semibold ${stage.state === 'todo' ? 'text-faint' : 'text-ink'}`}
              >
                {stage.name}
              </span>
            </div>
            <div className="mt-[4px] text-[11px] text-sub">{stage.sub}</div>
            <span className="sr-only">
              {stage.state === 'done'
                ? 'Complete.'
                : stage.state === 'current'
                  ? 'In progress.'
                  : 'Not started.'}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
