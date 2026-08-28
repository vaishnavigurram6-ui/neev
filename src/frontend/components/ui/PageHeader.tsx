// PageHeader.tsx — eyebrow + h1 + sub + right-aligned actions. Exactly one <h1>
// per page comes from here.
export default function PageHeader({
  eyebrow,
  title,
  sub,
  actions,
  status,
}: {
  /** Text, or a fragment where one word of it is a link — the Tranche Decision
   *  breadcrumb is "PORTFOLIO · LOAN 1001 — RAVI KUMAR · TRANCHE 4" with the
   *  first word linking back to the hotlist. Widened from `string` in Task 18;
   *  every existing caller passes a string and is unaffected. */
  eyebrow: React.ReactNode;
  title: string;
  sub?: string;
  actions?: React.ReactNode;
  /** A status marker for the page itself — the "Preview" pill on a scaffolded
   *  screen. It belongs beside the eyebrow, not in `actions`: a pill sitting in
   *  a row of buttons reads as one, and people click it. */
  status?: React.ReactNode;
}) {
  return (
    <div className="flex items-end justify-between gap-5">
      <div>
        <div className="flex items-center gap-[10px]">
          <div className="text-[12px] font-semibold uppercase tracking-[0.08em] text-faint">
            {eyebrow}
          </div>
          {status}
        </div>
        <h1 className="mt-2 font-display text-[28px] font-bold tracking-[-0.02em] text-ink">
          {title}
        </h1>
        {sub && <div className="mt-[6px] text-[14px] text-sub">{sub}</div>}
      </div>
      {actions && <div className="flex flex-none gap-[10px]">{actions}</div>}
    </div>
  );
}
