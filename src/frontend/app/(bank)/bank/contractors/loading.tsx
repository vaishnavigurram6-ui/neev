// Four states, not one (spec §6.5). The skeleton matches the scorecard's own
// layout — header, one table, two footer cards — so nothing jumps when the rows
// land.
import Skeleton from '@/components/ui/Skeleton';

export default function Loading() {
  return (
    <div className="flex flex-col gap-5">
      <Skeleton className="h-[74px] w-[460px]" />
      <Skeleton className="h-[280px]" />
      <div className="grid grid-cols-2 gap-4">
        <Skeleton className="h-[140px]" />
        <Skeleton className="h-[140px]" />
      </div>
    </div>
  );
}
