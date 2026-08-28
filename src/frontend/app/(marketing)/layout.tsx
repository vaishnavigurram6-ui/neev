// The pre-auth group: no nav, no profile chip, and — unlike (owner) and (bank) —
// no shared top bar, because the two screens in this group do not share one.
// Landing draws a 64px marketing header with its own links; Login is a
// full-height two-column split whose logo sits inside the left panel, with no bar
// at all. A layout-level <TopBar> would have to be hidden on one of the two.
//
// This is also the one group layout that sets no `robots` directive: the landing
// page is the only indexable route in the product, and Login opts itself out.
export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
