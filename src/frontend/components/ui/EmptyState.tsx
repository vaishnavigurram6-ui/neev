import Card from './Card';

export default function EmptyState({
  title,
  body,
  action,
}: {
  title: string;
  body: string;
  action?: React.ReactNode;
}) {
  return (
    <Card className="px-6 py-12 text-center">
      <h2 className="font-display text-[18px] font-semibold text-ink">{title}</h2>
      <p className="mx-auto mt-2 max-w-[46ch] text-[13px] text-sub">{body}</p>
      {action && <div className="mt-5 flex justify-center">{action}</div>}
    </Card>
  );
}
