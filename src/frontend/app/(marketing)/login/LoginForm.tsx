'use client';

// The login card, ported from the right column of `Neev Login.dc.html`.
//
// The prototype has no form at all: the role toggle is two <div>s, the phone
// field is a <div> holding placeholder text, and "Send OTP" is a <div> with a
// hover style. All of it is restored here — one <form>, two native radios in a
// radiogroup, a real tel input, and submit buttons that carry their intent — so
// the number is validated, the error is announced, and nothing depends on a
// click handler firing.
//
// Validation lives in the server action, not here, which is why the form is
// `noValidate`: the browser's own bubble cannot be pointed at the error slot the
// input is described by, and a client-only check is not a check.
import { useActionState, useEffect, useId, useRef, useState } from 'react';
import Button from '@/components/ui/Button';
import Card from '@/components/ui/Card';
import type { Role } from '@/lib/session';
import { loginAction } from './actions';
import { formatPhone, initialLoginState } from './state';

const ROLES: { value: Role; label: string }[] = [
  { value: 'owner', label: 'I’m building a home' },
  { value: 'bank', label: 'I’m a lender' },
];

export default function LoginForm({ initialRole, next }: { initialRole: Role; next: string }) {
  const [state, formAction, pending] = useActionState(loginAction, initialLoginState(initialRole));
  const [bankLinkOpen, setBankLinkOpen] = useState(false);

  const ids = useId();
  const phoneId = `${ids}-phone`;
  const phonePrefixId = `${ids}-prefix`;
  const codeId = `${ids}-code`;
  const codeHintId = `${ids}-code-hint`;
  const errorId = `${ids}-error`;
  const formErrorId = `${ids}-form-error`;
  const bankLinkId = `${ids}-bank-link`;

  const phoneRef = useRef<HTMLInputElement>(null);
  const codeRef = useRef<HTMLInputElement>(null);

  // Focus follows the failure, and follows the step forward when it succeeds.
  // A message nobody is looking at is not an error report.
  useEffect(() => {
    if (state.error?.field === 'phone') phoneRef.current?.focus();
    else if (state.error?.field === 'code') codeRef.current?.focus();
    else if (state.step === 'code') codeRef.current?.focus();
  }, [state]);

  const onPhone = state.step === 'phone';
  const fieldError = state.error && state.error.field !== 'form' ? state.error.message : null;

  return (
    <form action={formAction} noValidate className="w-full">
      <input type="hidden" name="next" value={next} />

      <h2 className="text-[23px] font-bold tracking-[-0.02em] text-ink">Welcome back</h2>

      {/* Native radios keep arrow-key navigation and submit their own value; the
          container carries role="radiogroup" so the pair is announced as one
          control. The visible pill is styled from :checked, so the selection
          survives a re-render without this component owning it. */}
      <div
        role="radiogroup"
        aria-label="Log in as"
        className="mt-[18px] flex rounded-[11px] bg-chip p-1 text-[13px] font-semibold"
      >
        {ROLES.map((role) => (
          <label key={role.value} className="flex-1">
            <input
              type="radio"
              name="role"
              value={role.value}
              defaultChecked={state.role === role.value}
              className="peer sr-only"
            />
            <span className="block cursor-pointer rounded-lg py-[9px] text-center text-sub peer-checked:bg-card peer-checked:text-ink peer-checked:shadow-card peer-focus-visible:outline-2 peer-focus-visible:outline-offset-2 peer-focus-visible:outline-[color:var(--focus)]">
              {role.label}
            </span>
          </label>
        ))}
      </div>

      <Card className="mt-4 p-6">
        {onPhone ? (
          <>
            <label htmlFor={phoneId} className="block text-[12.5px] font-semibold text-sub">
              Mobile number
            </label>
            <div className="mt-2 flex gap-2">
              <span
                id={phonePrefixId}
                className="tnum rounded-[10px] border border-input-border px-3 py-[11px] text-[13.5px] text-sub"
              >
                +91
              </span>
              <input
                ref={phoneRef}
                id={phoneId}
                name="phone"
                type="tel"
                inputMode="numeric"
                autoComplete="tel-national"
                defaultValue={formatPhone(state.phone)}
                placeholder="98490 12345"
                aria-describedby={`${phonePrefixId} ${errorId}`}
                aria-invalid={state.error?.field === 'phone' || undefined}
                className="tnum min-w-0 flex-1 rounded-[10px] border border-input-border bg-card px-[14px] py-[11px] text-[13.5px] text-ink placeholder:text-faint"
              />
            </div>
          </>
        ) : (
          <>
            <label htmlFor={codeId} className="block text-[12.5px] font-semibold text-sub">
              6-digit code
            </label>
            <p id={codeHintId} className="mt-1 text-[11.5px] text-faint">
              Sent to +91 {formatPhone(state.phone)}. Any six digits work in this build — no real
              SMS is sent.
            </p>
            <input
              ref={codeRef}
              id={codeId}
              name="code"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              placeholder="······"
              aria-describedby={`${codeHintId} ${errorId}`}
              aria-invalid={state.error?.field === 'code' || undefined}
              className="tnum mt-2 block w-full rounded-[10px] border border-input-border bg-card px-[14px] py-[11px] text-[15px] tracking-[0.3em] text-ink placeholder:text-faint"
            />
            {/* Carried forward so the POST is complete on its own terms. */}
            <input type="hidden" name="phone" value={state.phone} />
          </>
        )}

        {/* Always in the tree so it is a live region before it has anything to
            say; `empty:hidden` keeps it out of the layout until it does. */}
        <p
          id={errorId}
          role="alert"
          className="mt-2 text-[12px] font-semibold text-danger empty:hidden"
        >
          {fieldError}
        </p>

        <Button
          type="submit"
          name="intent"
          value={onPhone ? 'send-code' : 'verify'}
          variant="primary"
          disabled={pending}
          className="mt-[14px] w-full py-3 text-[14px]"
        >
          {onPhone
            ? pending
              ? 'Sending OTP…'
              : 'Send OTP'
            : pending
              ? 'Logging you in…'
              : 'Log in'}
        </Button>

        <p
          id={formErrorId}
          role="alert"
          className="mt-2 text-center text-[12px] font-semibold text-danger empty:hidden"
        >
          {state.error?.field === 'form' ? state.error.message : null}
        </p>

        {onPhone ? (
          <>
            <div className="my-[18px] flex items-center gap-3">
              <span className="h-px flex-1 bg-line" />
              <span className="text-[11.5px] text-faint">or</span>
              <span className="h-px flex-1 bg-line" />
            </div>

            {/* The prototype gives this fallback no destination, and there is no
                magic-link endpoint to send it to. Rather than a dead control, it
                is a disclosure that says where the link actually comes from —
                the same choice AccessibilityCluster makes for the out-of-scope
                language and listen-aloud affordances. */}
            <Button
              variant="outline"
              className="w-full py-3 text-[13.5px]"
              aria-expanded={bankLinkOpen}
              aria-controls={bankLinkOpen ? bankLinkId : undefined}
              onClick={() => setBankLinkOpen((open) => !open)}
            >
              Continue with the link your bank sent
            </Button>
            {bankLinkOpen && (
              <p id={bankLinkId} className="mt-2 text-[11.5px] leading-[1.55] text-faint">
                Your bank sends that link by SMS or WhatsApp — opening it signs you in without a
                code. This build cannot send one yet, so use your number above.
              </p>
            )}

            <p className="mt-3 text-center text-[11.5px] leading-[1.5] text-faint">
              No passwords. Your number is your login.
            </p>
          </>
        ) : (
          <Button
            type="submit"
            name="intent"
            value="change-number"
            variant="ghost"
            disabled={pending}
            className="mt-3 w-full py-2 text-[12.5px]"
          >
            Use a different number
          </Button>
        )}
      </Card>
    </form>
  );
}
