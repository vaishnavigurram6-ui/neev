// PreviewEmpty.tsx — the empty state the scaffolded screens show for a loan the
// fixtures do not cover. The prototypes only ever draw the populated state; this
// is the honest alternative to rendering the golden case's figures under someone
// else's name.
import Button from '@/components/ui/Button';
import EmptyState from '@/components/ui/EmptyState';

export default function PreviewEmpty({
  loanId,
  what,
}: {
  loanId: string;
  /** What this screen would have shown, in the owner's words. */
  what: string;
}) {
  return (
    <EmptyState
      title="Nothing to show for this loan yet"
      body={`${what} We only have the seeded build data for the demo case, so this preview screen has nothing of yours to draw.`}
      action={
        <Button href={`/owner/loans/${loanId}/boq`} variant="primary">
          Back to my contract
        </Button>
      }
    />
  );
}
