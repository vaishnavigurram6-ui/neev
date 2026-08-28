import Skeleton from '@/components/ui/Skeleton';

export default function Loading() {
  return (
    <div className="flex flex-col gap-5">
      <Skeleton className="h-[74px] w-[520px]" />
      <Skeleton className="h-[64px]" />
      <div className="flex gap-5">
        <Skeleton className="h-[520px] flex-1" />
        <Skeleton className="h-[360px] w-[340px]" />
      </div>
    </div>
  );
}
