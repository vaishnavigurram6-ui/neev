// The sanction check reads two endpoints; either can fail. Retry re-runs the
// server component, so a backend that was down a moment ago recovers in place
// without the reader losing the page.
'use client';

import ErrorState from '@/components/ui/ErrorState';

export default function SanctionError({ reset }: { error: Error; reset: () => void }) {
  return (
    <ErrorState
      title="We could not run the sanction check"
      body="Your BoQ and your loan are safe — nothing has changed. Try again."
      onRetry={reset}
    />
  );
}
