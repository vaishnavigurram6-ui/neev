// The decision form's state, in its own module because a `'use server'` file may
// only export async functions — the same split as `(marketing)/login`.

/** The three outcomes the endpoint accepts. Mirrors `DecisionAction` in
 *  `src/backend/app/api/routes/tranches.py`. */
export const DECISION_ACTIONS = ['RELEASE', 'HOLD', 'ESCALATE'] as const;

export type DecisionAction = (typeof DECISION_ACTIONS)[number];

export function isDecisionAction(value: unknown): value is DecisionAction {
  return typeof value === 'string' && (DECISION_ACTIONS as readonly string[]).includes(value);
}

export interface DecisionState {
  status: 'idle' | 'ok' | 'error';
  /** Announced through an aria-live region, so it must read as a whole sentence. */
  message: string;
  /** What was recorded, on success — the card marks it so the officer can see
   *  which of the three actually went to the loan file. */
  recorded: DecisionAction | null;
}

export const INITIAL_DECISION_STATE: DecisionState = {
  status: 'idle',
  message: '',
  recorded: null,
};
