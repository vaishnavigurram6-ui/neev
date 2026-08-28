'use client';

import ErrorState from '@/components/ui/ErrorState';

export default function ContractorsError({ reset }: { error: Error; reset: () => void }) {
  return (
    <ErrorState
      body="The contractor scorecard could not be loaded. Nothing on the book has changed — try again."
      onRetry={reset}
    />
  );
}
