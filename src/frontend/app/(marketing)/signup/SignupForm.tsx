'use client';

// The sign-up card. One step, six fields, three of which describe the loan.
//
// The loan fields are on this form rather than a later screen because a
// borrower with no loan has nothing to be shown: every owner screen reads
// `/api/loans/{id}`. With a loan, a brand-new account lands on its own contract
// page, honestly empty, with the upload control ready.
//
// Validation lives in the server action, not here, which is why the form is
// `noValidate`: the browser's own bubble cannot be pointed at the error slot
// the input is described by, and a client-only check is not a check.
import { useActionState, useEffect, useId, useRef } from 'react';
import Button from '@/components/ui/Button';
import { signupAction } from './actions';
import { initialSignupState, type SignupField } from './state';

const FIELDS: {
  name: SignupField;
  label: string;
  hint?: string;
  type?: string;
  autoComplete?: string;
  placeholder?: string;
  optional?: boolean;
}[] = [
  { name: 'name', label: 'Your name', autoComplete: 'name', placeholder: 'Lakshmi Reddy' },
  {
    name: 'username',
    label: 'Username',
    hint: 'Lowercase letters, numbers, dots, dashes or underscores.',
    autoComplete: 'username',
    placeholder: 'lakshmi',
  },
  {
    name: 'password',
    label: 'Password',
    hint: 'At least 8 characters.',
    type: 'password',
    autoComplete: 'new-password',
  },
  { name: 'locality', label: 'Where the plot is', placeholder: 'Miyapur, Hyderabad' },
  {
    name: 'sanctioned',
    label: 'Amount sanctioned',
    hint: 'The figure on your sanction letter.',
    placeholder: '32,00,000',
  },
  {
    name: 'built_up_sqft',
    label: 'Built-up area',
    hint: 'Square feet. Leave blank if you are not sure yet.',
    placeholder: '1,450',
    optional: true,
  },
];

export default function SignupForm() {
  const [state, formAction, pending] = useActionState(signupAction, initialSignupState());

  const ids = useId();
  const errorId = `${ids}-error`;
  const refs = useRef<Record<string, HTMLInputElement | null>>({});

  // Focus follows the failure. A message nobody is looking at is not an error
  // report.
  useEffect(() => {
    const field = state.error?.field;
    if (field && field !== 'form') refs.current[field]?.focus();
  }, [state]);

  const formError = state.error?.field === 'form' ? state.error.message : null;

  return (
    <form action={formAction} noValidate className="w-full">
      {FIELDS.map((f) => {
        const id = `${ids}-${f.name}`;
        const failed = state.error?.field === f.name;
        const hintId = f.hint ? `${id}-hint` : undefined;
        return (
          <div key={f.name} className="mt-[14px] first:mt-6">
            <label htmlFor={id} className="block text-[12.5px] font-semibold text-sub">
              {f.label}
              {f.optional ? <span className="font-normal text-faint"> — optional</span> : null}
            </label>
            <input
              id={id}
              ref={(node) => {
                refs.current[f.name] = node;
              }}
              name={f.name}
              type={f.type ?? 'text'}
              defaultValue={
                f.name === 'password'
                  ? undefined
                  : state.values[f.name as keyof typeof state.values]
              }
              autoComplete={f.autoComplete}
              autoCapitalize={f.name === 'username' ? 'none' : undefined}
              spellCheck={f.name === 'username' ? false : undefined}
              placeholder={f.placeholder}
              aria-describedby={[failed ? errorId : null, hintId].filter(Boolean).join(' ') || undefined}
              aria-invalid={failed || undefined}
              className="mt-[6px] w-full rounded-[10px] border border-input-border bg-card px-[14px] py-[11px] text-[13.5px] text-ink placeholder:text-faint"
            />
            {/* The rule, always visible -- not revealed only once it has been
                broken. A hint that appears as an error is a rule the visitor
                was never told. */}
            {f.hint ? (
              <p id={hintId} className="mt-[5px] text-[11.5px] leading-[1.5] text-faint">
                {f.hint}
              </p>
            ) : null}
            {failed ? (
              <p id={errorId} role="alert" className="mt-[5px] text-[12px] font-semibold text-danger">
                {state.error?.message}
              </p>
            ) : null}
          </div>
        );
      })}

      {formError ? (
        <p role="alert" className="mt-3 text-[12px] font-semibold text-danger">
          {formError}
        </p>
      ) : null}

      <Button
        type="submit"
        variant="primary"
        disabled={pending}
        className="mt-5 w-full py-3 text-[14px]"
      >
        {pending ? 'Creating your account…' : 'Create account'}
      </Button>
    </form>
  );
}
