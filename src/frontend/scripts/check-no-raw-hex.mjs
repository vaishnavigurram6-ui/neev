// Fails the build on a raw #rrggbb outside the theme file.
//
// The mockups hardcode hex hundreds of times across fifteen files. If that
// survives the port, retoning becomes impossible and the screens drift apart —
// and the handoff README explicitly warns the palette was still under
// discussion. Colours come from theme tokens, only.

import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';

const ROOT = process.cwd();
const ALLOWED = new Set(['app/globals.css']);
const EXTS = ['.ts', '.tsx', '.css', '.mjs'];
const SKIP_DIRS = new Set(['node_modules', '.next', 'out', '.git']);
const HEX = /#[0-9a-fA-F]{3,8}\b/g;

function walk(dir, out = []) {
  for (const entry of readdirSync(dir)) {
    if (SKIP_DIRS.has(entry)) continue;
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) walk(full, out);
    else if (EXTS.some((e) => entry.endsWith(e))) out.push(full);
  }
  return out;
}

const offenders = [];
for (const file of walk(ROOT)) {
  const rel = relative(ROOT, file).split('\\').join('/');
  if (ALLOWED.has(rel) || rel.startsWith('scripts/')) continue;
  const lines = readFileSync(file, 'utf8').split('\n');
  lines.forEach((line, i) => {
    if (line.includes('check-no-raw-hex')) return;
    for (const match of line.match(HEX) ?? []) {
      offenders.push(`${rel}:${i + 1}  ${match}`);
    }
  });
}

if (offenders.length) {
  console.error('Raw hex colours found outside app/globals.css:\n');
  for (const o of offenders) console.error('  ' + o);
  console.error(
    `\n${offenders.length} violation(s). Add a token in app/globals.css and use it instead.`
  );
  process.exit(1);
}
console.log('No raw hex outside the theme file.');
