// Button.tsx — the prototypes contain not one <button>. Every control there is a
// styled <div>: not focusable, not announced, not submittable. This restores the
// semantics. Actions are <button>; navigation is <a>.
//
// The two shapes are a discriminated union rather than one prop bag, because a
// single `ButtonHTMLAttributes` bag lets `<Button href="/x" disabled>` typecheck
// and then silently render a fully clickable link: the props would be spread onto
// the <button> branch only. With the union, button-only attributes are a type
// error alongside `href`, and the link branch forwards its own anchor attributes.
import Link from 'next/link';
import type { AnchorHTMLAttributes, ButtonHTMLAttributes } from 'react';
import type { Skin } from '@/lib/tone';

type Variant = 'primary' | 'outline' | 'ghost';

const SHAPE: Record<Skin, string> = {
  owner: 'rounded-pill',
  bank: 'rounded-bank',
};

const VARIANT: Record<Variant, string> = {
  primary: 'bg-action text-on-action hover:bg-action-hover',
  outline: 'border border-input-border bg-card text-ink hover:border-ink',
  ghost: 'text-sub hover:bg-chip hover:text-ink',
};

interface Common {
  variant?: Variant;
  skin?: Skin;
  className?: string;
  children?: React.ReactNode;
}

type LinkProps = Common &
  Omit<AnchorHTMLAttributes<HTMLAnchorElement>, keyof Common | 'href'> & { href: string };

type ButtonProps = Common &
  Omit<ButtonHTMLAttributes<HTMLButtonElement>, keyof Common> & { href?: undefined };

function classesFor(variant: Variant = 'outline', skin: Skin = 'owner', className = ''): string {
  return `inline-flex items-center justify-center gap-2 px-4 py-[10px] text-[13.5px] font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-55 ${SHAPE[skin]} ${VARIANT[variant]} ${className}`;
}

export default function Button(props: LinkProps | ButtonProps) {
  if (props.href !== undefined) {
    const { href, variant, skin, className, children, ...rest } = props;
    return (
      <Link href={href} className={classesFor(variant, skin, className)} {...rest}>
        {children}
      </Link>
    );
  }

  const { variant, skin, className, children, ...rest } = props;
  return (
    <button type="button" className={classesFor(variant, skin, className)} {...rest}>
      {children}
    </button>
  );
}
