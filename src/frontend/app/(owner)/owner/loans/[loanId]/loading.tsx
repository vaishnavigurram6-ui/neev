// Skeletons match the final layout so nothing jumps when the data lands.
import Skeleton from '@/components/ui/Skeleton';

export default function Loading() {
  return (
    <div className="flex flex-col gap-5">
      <Skeleton className="h-[74px] w-[440px]" />
      <div className="grid grid-cols-4 gap-4">
        {[0, 1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-[104px]" />
        ))}
      </div>
      <div className="flex gap-5">
        <Skeleton className="h-[420px] flex-1" />
        <Skeleton className="h-[300px] w-[340px]" />
      </div>
    </div>
  );
}
