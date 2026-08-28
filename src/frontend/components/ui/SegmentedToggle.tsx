'use client';

// Filters and tabs belong in the URL (spec §6.6), so a shared link reproduces
// what the sender saw — which matters when a credit officer sends a loan to a
// colleague. This component therefore navigates rather than holding state.
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { useRef } from 'react';
import type { Skin } from '@/lib/tone';

export interface ToggleOption {
  value: string;
  label: string;
}

export default function SegmentedToggle({
  options,
  value,
  paramName,
  skin = 'owner',
  label,
}: {
  options: ToggleOption[];
  value: string;
  paramName: string;
  skin?: Skin;
  label: string;
}) {
  const pathname = usePathname();
  const params = useSearchParams();
  const refs = useRef<(HTMLAnchorElement | null)[]>([]);

  const hrefFor = (next: string) => {
    const query = new URLSearchParams(params.toString());
    query.set(paramName, next);
    return `${pathname}?${query.toString()}`;
  };

  const onKeyDown = (event: React.KeyboardEvent, index: number) => {
    const delta = event.key === 'ArrowRight' ? 1 : event.key === 'ArrowLeft' ? -1 : 0;
    if (!delta) return;
    event.preventDefault();
    const next = (index + delta + options.length) % options.length;
    refs.current[next]?.focus();
  };

  const radius = skin === 'bank' ? 'rounded-bank' : 'rounded-pill';

  // Roving tabindex needs exactly one tabbable option. A shared link carrying a
  // stale or unknown `?param=` value matches nothing, and without this fallback
  // every option would be tabIndex -1 — the control would be unreachable by
  // keyboard precisely in the case this URL-driven design makes routine.
  const selectedIndex = options.findIndex((option) => option.value === value);
  const tabbableIndex = selectedIndex === -1 ? 0 : selectedIndex;

  return (
    <div role="tablist" aria-label={label} className={`inline-flex gap-1 bg-chip p-1 ${radius}`}>
      {options.map((option, index) => {
        const selected = index === selectedIndex;
        return (
          <Link
            key={option.value}
            ref={(node) => {
              refs.current[index] = node;
            }}
            href={hrefFor(option.value)}
            role="tab"
            aria-selected={selected}
            tabIndex={index === tabbableIndex ? 0 : -1}
            onKeyDown={(event) => onKeyDown(event, index)}
            scroll={false}
            className={`px-[13px] py-[6px] text-[12.5px] font-semibold transition-colors ${radius} ${
              selected ? 'bg-card text-ink shadow-card' : 'text-sub hover:text-ink'
            }`}
          >
            {option.label}
          </Link>
        );
      })}
    </div>
  );
}
