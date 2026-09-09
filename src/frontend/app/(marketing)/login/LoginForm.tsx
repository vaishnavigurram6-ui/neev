'use client';

// The login card. One step: a username and a password.
//
// The "Welcome back" heading lives in page.tsx, not here, so the role toggle can
// sit on the same line as it. Both are static; only the fields need a client.
//
// It lists no accounts. It used to, as a hint for judges, and that is
// documentation rather than interface: a product does not tell a visitor whose
// account to borrow. The demo credentials live in docs/Neev_Demo_Runbook.md.
//
// It was two — a phone number, then a six-digit code that accepted any six
// digits. Nobody could narrate that honestly ("type any number, then any
// code"), and it mapped every owner onto loan 1001 however they signed in, so
// two people in a demo silently overwrote each other's work. Named accounts
// fixed both; see `app/api/accounts.py`.
//
// Validation lives in the server action, not here, which is why the form is
// `noValidate`: the browser's own bubble cannot be pointed at the error slot
// the input is described by, and a client-only check is not a check.
import { useActionState, useEffect, useId, useRef } from 'react';
import Button from '@/components/ui/Button';
import { loginAction } from './actions';
import { initialLoginState } from './state';

export default function LoginForm({ next }: { next: string }) {
  const [state, formAction, pending] = useActionState(loginAction, initialLoginState());

  const ids = useId();
  const usernameId = `${ids}-username`;
  const passwordId = `${ids}-password`;
  const errorId = `${ids}-error`;

  const usernameRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);

  // Focus follows the failure. A message nobody is looking at is not an error
  // report.
  useEffect(() => {
    if (state.error?.field === 'username') usernameRef.current?.focus();
    else if (state.error?.field === 'password') passwordRef.current?.focus();
  }, [state]);

  const fieldError = state.error && state.error.field !== 'form' ? state.error.message : null;
  const formError = state.error?.field === 'form' ? state.error.message : null;

  return (
    <form action={formAction} noValidate className="w-full">
      <input type="hidden" name="next" value={next} />

      <label htmlFor={usernameId} className="mt-6 block text-[12.5px] font-semibold text-sub">
        Username
      </label>
      <input
        id={usernameId}
        ref={usernameRef}
        name="username"
        defaultValue={state.username}
        autoComplete="username"
        autoCapitalize="none"
        spellCheck={false}
        placeholder="ravi"
        aria-describedby={errorId}
        aria-invalid={state.error?.field === 'username' || undefined}
        className="mt-[6px] w-full rounded-[10px] border border-input-border bg-card px-[14px] py-[11px] text-[13.5px] text-ink placeholder:text-faint"
      />

      <label htmlFor={passwordId} className="mt-4 block text-[12.5px] font-semibold text-sub">
        Password
      </label>
      <input
        id={passwordId}
        ref={passwordRef}
        name="password"
        type="password"
        autoComplete="current-password"
        aria-describedby={errorId}
        aria-invalid={state.error?.field === 'password' || undefined}
        className="mt-[6px] w-full rounded-[10px] border border-input-border bg-card px-[14px] py-[11px] text-[13.5px] text-ink"
      />

      {/* One slot for both kinds of failure, announced either way. */}
      <p
        id={errorId}
        role="alert"
        className="mt-2 text-[12px] font-semibold text-danger empty:hidden"
      >
        {fieldError ?? formError ?? ''}
      </p>

      <Button
        type="submit"
        variant="primary"
        disabled={pending}
        className="mt-[14px] w-full py-3 text-[14px]"
      >
        {pending ? 'Signing you in…' : 'Sign in'}
      </Button>

    </form>
  );
}
