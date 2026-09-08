// Auth is a mocked session with a real boundary: the cookie is fake, but the
// middleware redirect and the backend's get_current_user dependency are real, so
// OTP drops in later without touching any screen.
import { apiGet, ApiError } from './api';

export const SESSION_COOKIE = 'neev_session';

export type Role = 'owner' | 'bank';

export interface Session {
  role: Role;
  loanId: string;
  name: string;
  sub: string;
}

/** Cookie format: "role:loanId:name". Mocked, but parsed like a real claim set —
 *  which means every field is untrusted client input. A malformed cookie is
 *  "no session", never an exception: `decodeURIComponent` throws URIError on a
 *  lone `%`, and thrown from a layout that surfaces as a 500 error boundary on
 *  every route instead of a redirect to /login. */
export async function readSession(): Promise<Session | null> {
  try {
    const user = await apiGet<{ role: Role; loan_id: string; name: string; sub: string }>('/api/me');
    return { role: user.role, loanId: user.loan_id, name: user.name, sub: user.sub };
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null;
    throw error;
  }
}
