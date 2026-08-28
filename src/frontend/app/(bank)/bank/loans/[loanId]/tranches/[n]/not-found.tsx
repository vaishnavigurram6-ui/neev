import Button from '@/components/ui/Button';
import EmptyState from '@/components/ui/EmptyState';

export default function TrancheNotFound() {
  return (
    <EmptyState
      title="Loan not found in this portfolio."
      body="Check the loan id, or open the hotlist to find it."
      action={
        <Button href="/bank/portfolio" variant="primary" skin="bank">
          Back to portfolio
        </Button>
      }
    />
  );
}
