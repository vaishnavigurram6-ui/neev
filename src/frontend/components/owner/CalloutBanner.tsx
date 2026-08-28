// CalloutBanner.tsx — the full-width tinted banner: Build Progress's paused-
// release notice and the Revised Contract's all-clear. Both mockups draw the
// same shape with a different tint, so it takes `tone` from the one status
// vocabulary and gets its colours from `toneClasses` — no colour prop, no hex.
//
// It composes the kit's `Card`; the tint and the text colour are the only things
// it adds. The lead sentence is bold, exactly as the mockups have it, and the
// tone is never the only carrier of meaning: the words say what has happened.
import Card from '@/components/ui/Card';
import { toneClasses, type Skin, type Tone } from '@/lib/tone';

export default function CalloutBanner({
  tone,
  lead,
  body,
  action,
  skin = 'owner',
}: {
  tone: Tone;
  lead: string;
  body?: string;
  action?: React.ReactNode;
  skin?: Skin;
}) {
  const { bg, text } = toneClasses(tone, skin);
  return (
    <Card skin={skin} className={`flex items-center justify-between gap-5 px-[22px] py-[18px] ${bg}`}>
      <p className={`text-[13.5px] leading-[1.6] ${text}`}>
        <strong className="font-bold">{lead}</strong>
        {body ? ` ${body}` : ''}
      </p>
      {action && <div className="flex-none">{action}</div>}
    </Card>
  );
}
