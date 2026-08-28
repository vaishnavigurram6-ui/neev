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

/** Cookie format: "role:loanId:name". Mocked, but parsed like a real claim set. */
export async function readSession(): Promise<Session | null> {
  const raw = (await cookies()).get(SESSION_COOKIE)?.value;
  if (!raw) return null;
  const [role, loanId, ...nameParts] = raw.split(':');
  if (role !== 'owner' && role !== 'bank') return null;
  const name = decodeURIComponent(nameParts.join(':') || '');
  return {
    role,
    loanId: loanId || '1001',
    name: name || (role === 'owner' ? 'Ravi Kumar' : 'Credit officer'),
    sub: role === 'owner' ? 'Owner · Plot 47, Kompally' : 'Credit officer · Retail assets',
  };
}
