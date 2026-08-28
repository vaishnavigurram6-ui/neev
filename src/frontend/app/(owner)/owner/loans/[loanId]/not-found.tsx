import Button from '@/components/ui/Button';
import EmptyState from '@/components/ui/EmptyState';

export default function LoanNotFound() {
  return (
    <EmptyState
      title="We could not find that loan"
      body="The link may be out of date, or the loan may belong to a different account."
      action={
        <Button href="/owner/onboarding" variant="primary">
          Start a new check
        </Button>
      }
    />
  );
}
