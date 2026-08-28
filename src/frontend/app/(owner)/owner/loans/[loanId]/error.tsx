'use client';

import ErrorState from '@/components/ui/ErrorState';

export default function LoanError({ reset }: { error: Error; reset: () => void }) {
  return (
    <ErrorState
      body="Something went wrong loading this loan. Your data is safe — try again."
      onRetry={reset}
    />
  );
}
