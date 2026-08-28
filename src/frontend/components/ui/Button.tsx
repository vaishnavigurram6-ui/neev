// Button.tsx — the prototypes contain not one <button>. Every control there is a
// styled <div>: not focusable, not announced, not submittable. This restores the
// semantics. Actions are <button>; navigation is <a>.
import Link from 'next/link';
import type { ButtonHTMLAttributes } from 'react';
import type { Skin } from '@/lib/tone';

type Variant = 'primary' | 'outline' | 'ghost';

const SHAPE: Record<Skin, string> = {
  owner: 'rounded-pill',
  bank: 'rounded-bank',
};

const VARIANT: Record<Variant, string> = {
  primary: 'bg-action text-card hover:bg-action-hover',
  outline: 'border border-input-border bg-card text-ink hover:border-ink',
  ghost: 'text-sub hover:bg-chip hover:text-ink',
};

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  skin?: Skin;
  href?: string;
}

export default function Button({
  variant = 'outline',
  skin = 'owner',
  href,
  className = '',
  children,
  ...rest
}: Props) {
  const classes = `inline-flex items-center justify-center gap-2 px-4 py-[10px] text-[13.5px] font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-55 ${SHAPE[skin]} ${VARIANT[variant]} ${className}`;

  if (href) {
    return (
      <Link href={href} className={classes}>
        {children}
      </Link>
    );
  }
  return (
    <button type="button" className={classes} {...rest}>
      {children}
    </button>
  );
}
