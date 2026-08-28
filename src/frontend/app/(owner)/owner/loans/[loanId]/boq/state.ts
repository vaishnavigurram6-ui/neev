// The send-questions action's state, in its own module.
//
// It cannot live in `actions.ts`: a `'use server'` file publishes every export
// as a server action, so `initialSendState` would be compiled to an action
// reference rather than an object — `useActionState` would start with a
// function as its state, and an unintended POST endpoint would be registered
// for it. `app/(marketing)/login/state.ts` splits the same way for the same
// reason.

export interface SendQuestionsState {
  status: 'idle' | 'sent' | 'error';
  /** How many questions are now with the contractor, as the backend counts
   *  them, or null when it did not say — a 2xx with no body is still a send. */
  sent: number | null;
  message: string | null;
}

export const initialSendState: SendQuestionsState = { status: 'idle', sent: null, message: null };
