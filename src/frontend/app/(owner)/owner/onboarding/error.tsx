'use client';

// The route's own boundary. The page already renders an `ErrorState` for a
// backend that answers badly; this catches what it cannot — a render that throws,
// or a failure that is not an `ApiError` at all.
import ErrorState from '@/components/ui/ErrorState';

export default function OnboardingError({ reset }: { error: Error; reset: () => void }) {
  return (
    <ErrorState
      title="We could not open this page"
      body="Nothing you have entered has been sent anywhere. Try again — your contract has not been uploaded."
      onRetry={reset}
    />
  );
}
