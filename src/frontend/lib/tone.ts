// One status vocabulary for the whole product.
//
// The mockups carry six: BoQ flag pills, tranche status, question status, bank
// action pills, contractor tiers, and inspection confidence — each with its own
// hardcoded pillBg/pillFg pair. They all collapse into `tone`, resolved here.
// No component anywhere takes a colour prop.

export type Tone = 'danger' | 'warn' | 'success' | 'neutral';
export type Skin = 'owner' | 'bank';

export interface ToneClasses {
  /** Background + text for a pill. */
  pill: string;
  /** Text colour only, for figures and inline emphasis. */
  text: string;
  /** Tint background only, for row highlights. */
  bg: string;
}

const OWNER: Record<Tone, ToneClasses> = {
  danger: { pill: 'bg-danger-tint text-danger', text: 'text-danger', bg: 'bg-danger-tint' },
  warn: { pill: 'bg-warn-tint text-warn', text: 'text-warn', bg: 'bg-warn-tint' },
  success: { pill: 'bg-success-tint text-success', text: 'text-success', bg: 'bg-success-tint' },
  neutral: { pill: 'bg-chip text-sub', text: 'text-ink', bg: 'bg-chip' },
};

const BANK: Record<Tone, ToneClasses> = {
  danger: {
    pill: 'bg-bank-danger-tint text-bank-danger',
    text: 'text-bank-danger',
    bg: 'bg-bank-danger-tint',
  },
  warn: {
    pill: 'bg-bank-warn-tint text-bank-warn',
    text: 'text-bank-warn',
    bg: 'bg-bank-warn-tint',
  },
  success: {
    pill: 'bg-bank-success-tint text-bank-success',
    text: 'text-bank-success',
    bg: 'bg-bank-success-tint',
  },
  neutral: { pill: 'bg-chip text-sub', text: 'text-ink', bg: 'bg-chip' },
};

export function toneClasses(tone: Tone, skin: Skin = 'owner'): ToneClasses {
  return (skin === 'bank' ? BANK : OWNER)[tone];
}

/** Maps a pipeline recommendation to a tone and the label the designs show. */
export function recommendationTone(
  recommendation: 'RELEASE' | 'HOLD' | 'ESCALATE' | 'INSPECT'
): { tone: Tone; label: string } {
  switch (recommendation) {
    case 'HOLD':
      return { tone: 'danger', label: 'HOLD' };
    case 'ESCALATE':
      return { tone: 'danger', label: 'ESCALATE' };
    case 'INSPECT':
      return { tone: 'warn', label: 'INSPECT' };
    case 'RELEASE':
      return { tone: 'success', label: 'ON TRACK' };
  }
}
