'use client';

import ErrorState from '@/components/ui/ErrorState';

export default function TrancheError({ reset }: { error: Error; reset: () => void }) {
  return (
    <ErrorState
      title="Could not load this tranche"
      body="The decision record was not returned. No decision has been written. Retry."
      onRetry={reset}
      skin="bank"
    />
  );
}
