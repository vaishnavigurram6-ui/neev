// Four states, not one (spec §6.5). The skeleton is the hotlist's own layout —
// header, four cards, one long table, the footnote row — so nothing on the page
// jumps when the book lands.
import Skeleton from '@/components/ui/Skeleton';

export default function Loading() {
  return (
    <div className="flex flex-col gap-5">
      <Skeleton className="h-[74px] w-[520px]" />
      <div className="grid grid-cols-4 gap-3">
        <Skeleton className="h-[104px]" />
        <Skeleton className="h-[104px]" />
        <Skeleton className="h-[104px]" />
        <Skeleton className="h-[104px]" />
      </div>
      <Skeleton className="h-[430px]" />
      <Skeleton className="h-[16px] w-[420px]" />
    </div>
  );
}
