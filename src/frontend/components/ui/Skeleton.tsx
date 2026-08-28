// Every data-driven screen implements four states, not one. The prototypes only
// ever show the populated state — the single easiest thing to forget when
// porting from a mockup.
export default function Skeleton({ className = '' }: { className?: string }) {
  return <div aria-hidden="true" className={`animate-pulse rounded-[8px] bg-chip ${className}`} />;
}
