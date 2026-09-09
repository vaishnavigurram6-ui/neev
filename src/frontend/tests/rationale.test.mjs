// The rationale parser runs on model output, so what it does with a shape it
// does not recognise matters as much as what it does with one it does.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { parseRationale } from '../app/(bank)/bank/loans/[loanId]/tranches/[n]/rationale.ts';

const OFFICER = `DISBURSAL RECOMMENDATION: HOLD

1. Key Risk & Financial Metrics:
- Sanctioned Loan Amount: ₹2,800,000
- Exposure Ratio: 1.11 (Disbursed ₹1,800,000 / Verified ₹1,617,897 > 1.0 threshold)

2. Verification & BOQ Audit Findings:
- Physical Stage Verification: Stage verified as 'slab' with high confidence.

3. Conclusion:
Disbursal hold recommended due to exposure ratio of 1.11.`;

test('the verdict is lifted out, so the page does not state it twice', () => {
  const blocks = parseRationale(OFFICER);
  assert.deepEqual(blocks[0], {
    kind: 'verdict',
    label: 'DISBURSAL RECOMMENDATION',
    value: 'HOLD',
  });
  // And only at the top: a shouted line later in the text is prose.
  const later = parseRationale('Some prose.\n\nSHOUTED LABEL: value');
  assert.equal(later.filter((b) => b.kind === 'verdict').length, 0);
});

test('numbered lines split into headings and instructions by their colon', () => {
  const blocks = parseRationale(OFFICER);
  const headings = blocks.filter((b) => b.kind === 'heading').map((b) => b.text);
  assert.deepEqual(headings, [
    'Key Risk & Financial Metrics',
    'Verification & BOQ Audit Findings',
    'Conclusion',
  ]);

  const asks = parseRationale(
    '1. Rate Adjustments: Items 2.3 and 3.1 are 22% over benchmark. Realign?\n' +
      '2. GST Alignment: Are rates inclusive of GST?'
  );
  assert.equal(asks.length, 1);
  assert.equal(asks[0].kind, 'steps');
  assert.deepEqual(
    asks[0].items.map((i) => i.title),
    ['Rate Adjustments', 'GST Alignment']
  );
  assert.match(asks[0].items[0].text, /^Items 2\.3/);
});

test('bullet runs become one block of label/value rows', () => {
  const [, , facts] = parseRationale(OFFICER);
  assert.equal(facts.kind, 'facts');
  assert.deepEqual(facts.rows, [
    { label: 'Sanctioned Loan Amount', value: '₹2,800,000' },
    {
      label: 'Exposure Ratio',
      value: '1.11 (Disbursed ₹1,800,000 / Verified ₹1,617,897 > 1.0 threshold)',
    },
  ]);
});

test('a bullet with no label keeps its line rather than losing it', () => {
  const [block] = parseRationale('- Require builder re-negotiation before release');
  assert.equal(block.kind, 'facts');
  assert.deepEqual(block.rows, [
    { label: null, value: 'Require builder re-negotiation before release' },
  ]);
});

test('a sentence introducing a list becomes that list s heading', () => {
  const blocks = parseRationale(
    'Here is a breakdown of where your project stands:\n- Sanctioned: ₹28,00,000'
  );
  assert.deepEqual(blocks[0], {
    kind: 'heading',
    text: 'Here is a breakdown of where your project stands',
  });
  assert.equal(blocks[1].kind, 'facts');
});

test('wrapped prose rejoins into one paragraph per block', () => {
  const blocks = parseRationale(
    'We are placing a temporary hold\non your requested disbursal.\n\nThe second paragraph.'
  );
  assert.deepEqual(
    blocks.map((b) => b.text),
    ['We are placing a temporary hold on your requested disbursal.', 'The second paragraph.']
  );
});

test('unrecognised text is never dropped', () => {
  for (const text of ['', '   ', '\n\n', 'a', '???']) {
    const blocks = parseRationale(text);
    const kept = blocks.map((b) => ('text' in b ? b.text : '')).join('');
    if (text.trim()) assert.match(kept, /\S/, `dropped: ${JSON.stringify(text)}`);
    else assert.deepEqual(blocks, []);
  }
  // Every non-empty line of the real narrative survives in some block.
  const lines = OFFICER.split('\n').filter((l) => l.trim()).length;
  const blocks = parseRationale(OFFICER);
  const accounted =
    blocks.filter((b) => b.kind === 'verdict' || b.kind === 'heading' || b.kind === 'para').length +
    blocks.filter((b) => b.kind === 'facts').reduce((n, b) => n + b.rows.length, 0) +
    blocks.filter((b) => b.kind === 'steps').reduce((n, b) => n + b.items.length, 0);
  assert.equal(accounted, lines);
});
