'use client';

// NavTabs resolves its own active state.
//
// A route-group layout renders the TopBar, and a layout cannot know which child
// route rendered beneath it — so an `activeHref` prop could never be filled
// correctly (Task 11 Step 4). The component reads `usePathname()` instead.
// Prefix matching keeps the parent tab lit on nested routes: /boq/revise still
// highlights "My contract".
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type { NavItem } from '@/lib/nav';
import type { Skin } from '@/lib/tone';

function isActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export default function NavTabs({ items, skin }: { items: NavItem[]; skin: Skin }) {
  const pathname = usePathname() ?? '';

  return (
    <nav aria-label="Primary" className="flex gap-1 text-[13.5px] font-medium">
      {items.map((item) => {
        const active = isActive(pathname, item.href);
        const classes =
          skin === 'bank'
            ? active
              ? 'bg-bank-surface text-bank-bar'
              : 'text-bank-inactive hover:text-bank-surface'
            : active
              ? 'bg-ink text-card'
              : 'text-sub hover:bg-chip hover:text-ink';
        return (
          <Link
            key={item.href}
            href={item.href}
            aria-current={active ? 'page' : undefined}
            className={`rounded-lg px-[13px] py-[7px] transition-colors ${classes}`}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
