// Shaped like the screen it precedes — the centred header block, the phase card,
// the findings feed — so nothing jumps when the socket opens. Overrides the
// loan-level skeleton, which draws the four-stat-card layout the other owner
// screens use and this one does not.
import Skeleton from '@/components/ui/Skeleton';

export default function Loading() {
  return (
    <div className="mx-auto flex max-w-[680px] flex-col items-center">
      <Skeleton className="h-[38px] w-[280px] rounded-pill" />
      <Skeleton className="mt-5 h-[32px] w-[320px]" />
      <Skeleton className="mt-2 h-[20px] w-[420px]" />
      <Skeleton className="mt-7 h-[300px] w-full" />
      <Skeleton className="mt-5 h-[64px] w-full" />
    </div>
  );
}
