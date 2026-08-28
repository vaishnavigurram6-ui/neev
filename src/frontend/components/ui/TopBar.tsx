// TopBar.tsx — the bar recurs near-identically across ten prototype files,
// differing only in which tab carries the active styling. One component with a
// `skin` prop replaces all of it, and it is what makes the bank's dark console
// chrome automatic.
//
// There is no `activeHref` prop: NavTabs resolves the active tab from
// usePathname(), because a route-group layout cannot know which child route
// rendered beneath it (Task 11 Step 4).
import Link from 'next/link';
import AccessibilityCluster from './AccessibilityCluster';
import Logo from './Logo';
import NavTabs from './NavTabs';
import ProfileChip from './ProfileChip';
import type { NavItem } from '@/lib/nav';
import type { Skin } from '@/lib/tone';

export default function TopBar({
  skin,
  nav,
  user,
  showAccessibility = false,
  homeHref = '/',
}: {
  skin: Skin;
  nav: NavItem[];
  user?: { name: string; sub: string };
  showAccessibility?: boolean;
  homeHref?: string;
}) {
  const bar =
    skin === 'bank'
      ? 'bg-bank-bar border-b border-bank-bar'
      : 'bg-card/[0.92] backdrop-blur-[8px] border-b border-line';

  return (
    <header
      className={`sticky top-0 z-10 flex h-[58px] items-center justify-between px-7 ${bar}`}
    >
      <div className="flex items-center gap-[22px]">
        <Link href={homeHref} aria-label="Neev home">
          <Logo skin={skin} />
        </Link>
        {nav.length > 0 && <NavTabs items={nav} skin={skin} />}
      </div>
      <div className="flex items-center gap-[14px]">
        {showAccessibility && <AccessibilityCluster />}
        {user && <ProfileChip name={user.name} sub={user.sub} skin={skin} />}
      </div>
    </header>
  );
}
