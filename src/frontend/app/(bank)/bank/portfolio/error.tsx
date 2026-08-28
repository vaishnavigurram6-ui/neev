'use client';

// The hotlist is read-only, so a failure here changed nothing on the book — say
// that, because an officer who cannot see the table has no other way to know.
import ErrorState from '@/components/ui/ErrorState';

export default function PortfolioError({ reset }: { error: Error; reset: () => void }) {
  return (
    <ErrorState
      title="Could not load the portfolio"
      body="The book did not come back. Nothing has changed on any loan — try again."
      onRetry={reset}
      skin="bank"
    />
  );
}
