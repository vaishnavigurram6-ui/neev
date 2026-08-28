// The app-wide 404. Route-level not-found files handle unknown loans; this one
// catches an address that matches no route at all.
import Button from '@/components/ui/Button';
import EmptyState from '@/components/ui/EmptyState';

export const metadata = { title: 'Page not found' };

export default function NotFound() {
  return (
    <main className="mx-auto max-w-[1280px] px-7 pb-20 pt-9">
      <EmptyState
        title="That page is not here"
        body="The link may be out of date. Everything Neev has checked for you is still where you left it."
        action={
          <Button href="/" variant="primary">
            Back to Neev
          </Button>
        }
      />
    </main>
  );
}
