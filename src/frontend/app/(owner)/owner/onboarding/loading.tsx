// Shaped like the screen: centred headline, three-pill stepper, the upload card,
// then the four stage cards.
import Skeleton from '@/components/ui/Skeleton';

export default function Loading() {
  return (
    <div className="mx-auto flex w-full max-w-[960px] flex-col items-center">
      <Skeleton className="h-[80px] w-[560px]" />
      <Skeleton className="mt-3 h-[48px] w-[600px]" />
      <Skeleton className="mt-9 h-[38px] w-[520px] rounded-pill" />
      <Skeleton className="mt-7 h-[280px] w-full max-w-[640px]" />
      <div className="mt-[52px] grid w-full max-w-[720px] grid-cols-4 gap-3">
        {[0, 1, 2, 3].map((index) => (
          <Skeleton key={index} className="h-[130px]" />
        ))}
      </div>
    </div>
  );
}
