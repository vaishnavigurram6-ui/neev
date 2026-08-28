// StickyRail.tsx — the 340px right column. Stays a rail across 1280-1920px; no
// collapse behaviour is built (laptop-only, spec §6.7).
export default function StickyRail({ children }: { children: React.ReactNode }) {
  return (
    <aside className="sticky top-[86px] flex w-[340px] flex-none flex-col gap-4 self-start">
      {children}
    </aside>
  );
}
