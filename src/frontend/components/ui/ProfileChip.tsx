// The signed-in identity, and the menu behind it.
//
// The prototype draws this as a <div> with `cursor: pointer` and no behaviour —
// it looks clickable and is not. Here it is a real disclosure: <details>/<summary>
// gives keyboard operation, Escape, and correct announcement for free, with no
// client component and no state to keep in step.
//
// The menu carries the two things a signed-in person wants, and switching sides
// is the one a demo needs constantly — otherwise moving between the owner's view
// and the bank console means returning to /login and re-entering a number.
import { logOutAction, switchRoleAction } from '@/lib/session-actions';
import type { Skin } from '@/lib/tone';

export default function ProfileChip({
  name,
  sub,
  skin,
}: {
  name: string;
  sub: string;
  skin: Skin;
}) {
  const nameClass = skin === 'bank' ? 'text-card' : 'text-ink';
  const subClass = skin === 'bank' ? 'text-bank-inactive' : 'text-faint';
  const avatar = skin === 'bank' ? 'bg-bank-accent text-card' : 'bg-ink text-card';
  const initials = name
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase();

  // `skin` already says which console this is, so the side of the table needs no
  // prop of its own: the bank chrome is only ever rendered for a bank session.
  const other: 'owner' | 'bank' = skin === 'bank' ? 'owner' : 'bank';
  const otherLabel = other === 'bank' ? 'Switch to the lender view' : 'Switch to the owner view';

  return (
    <details className="relative [&[open]>summary>span:last-child]:rotate-180">
      <summary
        className="flex cursor-pointer list-none items-center gap-[10px] rounded-lg px-1 py-1 [&::-webkit-details-marker]:hidden"
        aria-label={`${name}. ${sub}. Account menu`}
      >
        <span className="text-right">
          <span className={`block text-[13px] font-semibold leading-[1.2] ${nameClass}`}>
            {name}
          </span>
          <span className={`block text-[11px] ${subClass}`}>{sub}</span>
        </span>
        <span
          className={`flex h-8 w-8 flex-none items-center justify-center rounded-full text-[12px] font-semibold ${avatar}`}
          aria-hidden="true"
        >
          {initials}
        </span>
        <span className={`text-[10px] transition-transform ${subClass}`} aria-hidden="true">
          ▾
        </span>
      </summary>

      <div className="absolute right-0 z-20 mt-2 w-[236px] overflow-hidden rounded-card border border-line bg-card shadow-card">
        <p className="border-b border-line px-4 py-3 text-[11px] leading-[1.5] text-faint">
          Signed in as <span className="font-semibold text-ink">{name}</span>
          <br />
          {sub}
        </p>

        <form action={switchRoleAction}>
          <input type="hidden" name="to" value={other} />
          <button
            type="submit"
            className="block w-full px-4 py-[11px] text-left text-[13px] font-semibold text-ink hover:bg-hover"
          >
            {otherLabel}
          </button>
        </form>

        <form action={logOutAction}>
          <button
            type="submit"
            className="block w-full border-t border-line px-4 py-[11px] text-left text-[13px] text-sub hover:bg-hover hover:text-ink"
          >
            Log out
          </button>
        </form>
      </div>
    </details>
  );
}
