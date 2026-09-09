// The sign-up form's state, shared by the client form and the server action.
//
// Its own module because `actions.ts` carries `'use server'`, and such a file
// may only export async functions -- a plain `initialSignupState` helper there
// would be a build error. Same split as the login form.

export type SignupField =
  | 'name'
  | 'username'
  | 'password'
  | 'locality'
  | 'sanctioned'
  | 'built_up_sqft'
  | 'form';

export interface SignupError {
  /** Which control the message belongs to. `form` is for failures that belong
   *  to no single field -- a taken username, or an unreachable backend. */
  field: SignupField;
  message: string;
}

/** Everything typed so far, so a rejected attempt does not empty the form.
 *  The password is never echoed back. */
export interface SignupValues {
  name: string;
  username: string;
  locality: string;
  sanctioned: string;
  built_up_sqft: string;
}

export interface SignupState {
  values: SignupValues;
  error: SignupError | null;
}

export const emptyValues: SignupValues = {
  name: '',
  username: '',
  locality: '',
  sanctioned: '',
  built_up_sqft: '',
};

export function initialSignupState(values: SignupValues = emptyValues): SignupState {
  return { values, error: null };
}
