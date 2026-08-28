// The parent [loanId]/loading.tsx skeletons a header, four stat cards and a
// two-column body. Sanction Check has no stat-card row, so it gets its own:
// header, the bars card, the shortfall banner, the gap table, and the rail.
// Same boxes in the same places as the real screen, so nothing jumps.
import Skeleton from '@/components/ui/Skeleton';

export default function Loading() {
  return (
    <div className="flex flex-col gap-5">
      <Skeleton className="h-[74px] w-[440px]" />
      <div className="flex items-start gap-5">
        <div className="flex min-w-0 flex-1 flex-col gap-5">
          <Skeleton className="h-[250px]" />
          <Skeleton className="h-[86px]" />
          <Skeleton className="h-[280px]" />
        </div>
        <div className="flex w-[340px] flex-none flex-col gap-4">
          <Skeleton className="h-[130px]" />
          <Skeleton className="h-[92px]" />
          <Skeleton className="h-[92px]" />
          <Skeleton className="h-[92px]" />
        </div>
      </div>
    </div>
  );
}
