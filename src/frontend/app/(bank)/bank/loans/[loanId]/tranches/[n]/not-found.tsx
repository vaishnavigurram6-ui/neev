import Button from '@/components/ui/Button';
import EmptyState from '@/components/ui/EmptyState';

export default function TrancheNotFound() {
  return (
    <EmptyState
      skin="bank"
      title="No such tranche on the book"
      body="Either the loan is not in this portfolio or it has no tranche with that number. Open the hotlist and drill in from the row."
      action={
        <Button href="/bank/portfolio" variant="primary" skin="bank">
          Back to portfolio
        </Button>
      }
    />
  );
}
