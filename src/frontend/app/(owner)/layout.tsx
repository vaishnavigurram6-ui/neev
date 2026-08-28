// Supplies the warm-neutral chrome so no screen re-implements it. Redirects
// rather than rendering a shell with no session — the middleware catches this
// first, but a layout that trusts the edge alone would leak a shell whenever the
// matcher changes.
import { redirect } from 'next/navigation';
import TopBar from '@/components/ui/TopBar';
import { ownerNavFor } from '@/lib/nav';
import { readSession } from '@/lib/session';

export const metadata = { robots: { index: false, follow: false } };

export default async function OwnerLayout({ children }: { children: React.ReactNode }) {
  const session = await readSession();
  if (!session || session.role !== 'owner') redirect('/login?next=/owner/onboarding');

  return (
    <>
      <TopBar
        skin="owner"
        nav={ownerNavFor(session.loanId)}
        user={{ name: session.name, sub: session.sub }}
        showAccessibility
        homeHref={`/owner/loans/${session.loanId}/boq`}
      />
      <main className="mx-auto max-w-[1280px] px-7 pb-20 pt-9">{children}</main>
    </>
  );
}
