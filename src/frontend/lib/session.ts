// Auth is a mocked session with a real boundary: the cookie is fake, but the
// middleware redirect and the backend's get_current_user dependency are real, so
// OTP drops in later without touching any screen.
import { cookies } from 'next/headers';

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
  const raw = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!raw) return null;
  const [role, loanId, ...nameParts] = raw.split(':');
  if (role !== 'owner' && role !== 'bank') return null;
  if (!loanId) return null;

  let name: string;
  try {
    name = decodeURIComponent(nameParts.join(':'));
  } catch {
    return null;
  }

  return {
    role,
    loanId,
    name: name || (role === 'owner' ? 'Ravi Kumar' : 'Credit officer'),
    sub: role === 'owner' ? 'Owner · Plot 47, Kompally' : 'Credit officer · Retail assets',
  };
}
