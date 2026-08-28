// The pre-auth chrome: logo only, no nav, no profile chip. The landing page is
// the only indexable route in the product, so this is the one group layout that
// sets no `robots` directive.
import TopBar from '@/components/ui/TopBar';

export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <TopBar skin="owner" nav={[]} homeHref="/" />
      {children}
    </>
  );
}
