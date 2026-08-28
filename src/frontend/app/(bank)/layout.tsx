// The bank console chrome: same layout system, dark ink top bar, no
// accessibility cluster (the owner-side language and listen-aloud affordances
// are not part of the officer console).
import { redirect } from 'next/navigation';
import TopBar from '@/components/ui/TopBar';
import { BANK_NAV } from '@/lib/nav';
import { readSession } from '@/lib/session';

export const metadata = { robots: { index: false, follow: false } };

export default async function BankLayout({ children }: { children: React.ReactNode }) {
  const session = await readSession();
  if (!session || session.role !== 'bank') redirect('/login?next=/bank/portfolio');

  return (
    <>
      <TopBar
        skin="bank"
        nav={BANK_NAV}
        user={{ name: session.name, sub: session.sub }}
        showAccessibility={false}
        homeHref="/bank/portfolio"
      />
      <main className="mx-auto max-w-[1280px] px-7 pb-20 pt-9">{children}</main>
    </>
  );
}
