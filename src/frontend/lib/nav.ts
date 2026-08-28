// Spec §7.3: Setup stays in the bank nav on *all* bank routes — it owns the
// thresholds that drive every recommendation, so it must remain reachable. The
// prototypes deleted it from three of four bank screens; that is a fragment
// artifact, not a decision.

export interface NavItem {
  href: string;
  label: string;
}

/** Owner nav, from the handoff: My contract · Sanction check · Build progress · Changes. */
export function ownerNavFor(loanId: string): NavItem[] {
  return [
    { href: `/owner/loans/${loanId}/boq`, label: 'My contract' },
    { href: `/owner/loans/${loanId}/sanction`, label: 'Sanction check' },
    { href: `/owner/loans/${loanId}/progress`, label: 'Build progress' },
    { href: `/owner/loans/${loanId}/changes`, label: 'Changes' },
  ];
}

export const BANK_NAV: NavItem[] = [
  { href: '/bank/portfolio', label: 'Portfolio' },
  { href: '/bank/contractors', label: 'Contractors' },
  { href: '/bank/setup', label: 'Setup' },
];
