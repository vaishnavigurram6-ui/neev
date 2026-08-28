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
  /** Why this control cannot be used. Renders as VISIBLE text beneath the
   *  button and is wired to it with aria-describedby.
   *
   *  A disabled button is removed from the tab order and its `title` never
   *  appears for a mouse user, so a title-only explanation reaches nobody: the
   *  control simply does nothing when clicked, with no reason given. Anything
   *  disabled in this product says why, out loud. */
  reason?: string;
}

type LinkProps = Common &
  Omit<AnchorHTMLAttributes<HTMLAnchorElement>, keyof Common | 'href'> & { href: string };

type ButtonProps = Common &
  Omit<ButtonHTMLAttributes<HTMLButtonElement>, keyof Common> & { href?: undefined };

function classesFor(variant: Variant = 'outline', skin: Skin = 'owner', className = ''): string {
  return `inline-flex items-center justify-center gap-2 px-4 py-[10px] text-[13.5px] font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-55 ${SHAPE[skin]} ${VARIANT[variant]} ${className}`;
}

/** A stable id from the text itself: no hook, so this stays usable in a server
 *  component, and identical for the same explanation on every render. */
function reasonId(reason: string): string {
  let hash = 0;
  for (let i = 0; i < reason.length; i += 1) hash = (hash * 31 + reason.charCodeAt(i)) | 0;
  return `why-${Math.abs(hash).toString(36)}`;
}

export default function Button(props: LinkProps | ButtonProps) {
  if (props.href !== undefined) {
    const { href, variant, skin, className, children, reason, ...rest } = props;
    void reason; // a link that goes somewhere has nothing to explain
    return (
      <Link href={href} className={classesFor(variant, skin, className)} {...rest}>
        {children}
      </Link>
    );
  }

  const { variant, skin, className, children, reason, ...rest } = props;
  const button = (
    <button
      type="button"
      className={classesFor(variant, skin, className)}
      aria-describedby={reason ? reasonId(reason) : undefined}
      {...rest}
    >
      {children}
    </button>
  );

  if (!reason) return button;

  return (
    <span className="flex flex-col items-start gap-[6px]">
      {button}
      <span id={reasonId(reason)} className="max-w-[210px] text-[11px] leading-[1.45] text-faint">
        {reason}
      </span>
    </span>
  );
}
