import Card from './Card';
import Button from './Button';

export default function ErrorState({
  title = 'We could not load this',
  body,
  retryHref,
  onRetry,
}: {
  title?: string;
  body: string;
  retryHref?: string;
  onRetry?: () => void;
}) {
  return (
    <Card className="px-6 py-12 text-center">
      <h2 className="font-display text-[18px] font-semibold text-ink">{title}</h2>
      <p className="mx-auto mt-2 max-w-[46ch] text-[13px] text-sub">{body}</p>
      <div className="mt-5 flex justify-center">
        {retryHref ? (
          <Button href={retryHref} variant="primary">
            Try again
          </Button>
        ) : (
          <Button variant="primary" onClick={onRetry}>
            Try again
          </Button>
        )}
      </div>
    </Card>
  );
}
