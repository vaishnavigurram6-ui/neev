// The subset of `LoanSummaryView` (src/backend/app/schemas/views.py) that the
// onboarding wizard and the Analyzing screen actually read.
//
// It is a local narrowing rather than an addition to `lib/types.ts` on purpose:
// `lib/` is frozen for this wave, and `LoanSummaryView` is not transcribed there
// yet. When `npm run gen:types` regenerates `lib/api-types.ts` from the
// backend's OpenAPI document, this interface should be deleted and the generated
// `LoanSummaryView` used in its place. Field names stay snake_case so that swap
// is a one-line import change.

/** Loan ids are short opaque strings ("1001").
 *
 *  Validated, never escaped, everywhere one is interpolated into a backend URL
 *  path. The id reaching a screen comes either from the route segment or from the
 *  `neev_session` cookie, and both are client input in this phase — the cookie is
 *  a mock with no signature, and `readSession()` only rejects an empty loan slot.
 *  A value of `../portfolio` resolves as a dot segment during URL parsing, which
 *  would turn the frontend server into a proxy for any backend GET the browser
 *  cannot reach on its own. */
const LOAN_ID = /^[A-Za-z0-9_-]{1,32}$/;

export function isLoanId(value: string): boolean {
  return LOAN_ID.test(value);
}

export interface LoanFacts {
  loan_id: string;
  borrower: string;
  locality: string;
  plot_label: string | null;
  built_up_sqft: number | null;
  sanctioned: number;
  disbursed: number;
  contractor: string | null;
  /** null when nothing has been analysed on this loan yet — which is what gates
   *  every "see the finished report" link. Linking to a BoQ page with no
   *  revision behind it answers 404. */
  latest_rev: number | null;
}

/** Keeps only the declared fields.
 *
 *  `apiGet<LoanFacts>()` types the response but does not reshape it, so the
 *  object still carries everything `LoanSummaryView` returns — the loan's
 *  recommendation, its exposure ratio, its cost-to-complete gap. Both screens
 *  hand this to a client component, and a client component's props are
 *  serialised into the page. Passing the whole view would ship the bank's
 *  assessment of the borrower into their own HTML for no reason. */
export function pickLoanFacts(view: LoanFacts): LoanFacts {
  return {
    loan_id: view.loan_id,
    borrower: view.borrower,
    locality: view.locality,
    plot_label: view.plot_label,
    built_up_sqft: view.built_up_sqft,
    sanctioned: view.sanctioned,
    disbursed: view.disbursed,
    contractor: view.contractor,
    latest_rev: view.latest_rev,
  };
}
