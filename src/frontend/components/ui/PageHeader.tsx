// PageHeader.tsx — eyebrow + h1 + sub + right-aligned actions. Exactly one <h1>
// per page comes from here.
export default function PageHeader({
  eyebrow,
  title,
  sub,
  actions,
}: {
  eyebrow: string;
  title: string;
  sub?: string;
  actions?: React.ReactNode;
}) {
  return (
    <div className="flex items-end justify-between gap-5">
      <div>
        <div className="text-[12px] font-semibold uppercase tracking-[0.08em] text-faint">
          {eyebrow}
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
