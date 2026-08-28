// The Landing header. Not the kit's <TopBar>: this bar is 64px with a wider
// gutter, carries no nav tabs and no profile chip, and ends in two links plus the
// theme toggle — <TopBar> has no slot for those and the kit is frozen. Login
// draws no bar at all (its logo sits inside the left panel), which is why the
// (marketing) layout does not own this.
import Link from 'next/link';
import Button from '@/components/ui/Button';
import Logo from '@/components/ui/Logo';
import ThemeToggle from '@/components/ui/ThemeToggle';

export default function MarketingHeader() {
  return (
    <header className="flex h-16 flex-none items-center justify-between px-10">
      <Link href="/" aria-label="Neev home">
        <Logo size={26} />
      </Link>
      <div className="flex items-center gap-[18px] text-[13.5px] font-semibold">
        {/* The prototype points this at Neev 7 Bank Onboarding, which is
            /bank/setup — a gated route, so the middleware would bounce a visitor
            with no session to /login and, carrying no role, land them on the
            *owner* side of the toggle. Linking through login directly says which
            side of the table this is and keeps /bank/setup as the destination. */}
        <Link
          href="/login?role=bank&next=%2Fbank%2Fsetup"
          className="text-sub hover:text-action"
        >
          For lenders
        </Link>
        <ThemeToggle />
        <Button href="/login" variant="outline" className="px-[18px]">
          Log in
        </Button>
      </div>
    </header>
  );
}
