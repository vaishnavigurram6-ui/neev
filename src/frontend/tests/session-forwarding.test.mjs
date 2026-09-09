// The one correct way to send this visitor's session to the backend.
//
// Next percent-encodes cookie values when it writes them, so the header a
// browser sends holds `neev_session=owner%3A1001%3AUmF2aSBLdW1hcg%3A...` while
// the backend signs and parses `owner:1001:UmF2aSBLdW1hcg:...`. `cookies()`
// decodes on read; forwarding the incoming `cookie` header does not, and the
// backend's `_parse_cookie` then finds no colons and reads it as no session at
// all — which is how a signed-in owner's BoQ upload came back "No session.
// Sign in at POST /api/auth/session.", quoted verbatim into the wizard.
//
// Both relays are the only code that talks to the backend outside lib/api.ts,
// so this is a source-level invariant rather than a behavioural test: nothing
// on this path may read a cookie off its own request.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const RELAYS = [
  'app/api/loans/[loanId]/boq/route.ts',
  'app/api/jobs/[jobId]/events/route.ts',
];

test('relays forward the session through cookies(), never a raw request header', () => {
  for (const relay of RELAYS) {
    const source = readFileSync(new URL(`../${relay}`, import.meta.url), 'utf8');
    assert.match(source, /sessionCookieHeader\(\)/, `${relay} must use sessionCookieHeader()`);
    assert.doesNotMatch(
      source,
      /headers\.get\(\s*['"`]cookie['"`]\s*\)/i,
      `${relay} must not forward the raw cookie header — it is percent-encoded`
    );
  }
});

test('sessionCookieHeader is the only cookie read outside it', () => {
  const api = readFileSync(new URL('../lib/api.ts', import.meta.url), 'utf8');
  // One `cookies().get(...)` in the whole module, inside the helper.
  assert.equal((api.match(/cookies\(\)\)\.get\(/g) ?? []).length, 1);
  assert.match(api, /export async function sessionCookieHeader\(\)/);
});
