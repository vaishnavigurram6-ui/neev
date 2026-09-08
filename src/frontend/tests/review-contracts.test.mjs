import assert from 'node:assert/strict';
import { test } from 'node:test';
import { parsePipelineEvent, safeRedirect, reduce, EMPTY } from '../components/owner/analyzing-events.ts';
import { looksReadable, MAX_UPLOAD_BYTES } from '../components/owner/upload-validation.ts';

test('error and terminal SSE frames remain distinct for failed jobs', () => {
  const failure = parsePipelineEvent(JSON.stringify({type: 'error', message: 'Save failed'}));
  const done = parsePipelineEvent(JSON.stringify({type: 'done', redirect: '/owner/loans/1001/boq'}));
  assert.equal(failure.type, 'error');
  assert.equal(failure.message, 'Save failed');
  assert.equal(done.type, 'done');
  const state = reduce(reduce(EMPTY, {kind: 'event', event: failure}), {kind: 'event', event: done});
  assert.equal(state.finished, true);
  assert.equal(state.failure, 'Save failed');
});

test('SSE replay frames parse consistently, malformed frames do not crash', () => {
  const frame = JSON.stringify({type: 'phase', index: 1, name: 'Checking', status: 'done'});
  assert.deepEqual(parsePipelineEvent(frame), parsePipelineEvent(frame));
  const finding = {type: 'finding', flag: 'Rate', tone: 'danger', text: 'Check'};
  const first = reduce(EMPTY, {kind: 'event', event: finding});
  const replay = reduce(reduce(first, {kind: 'reset'}), {kind: 'event', event: finding});
  assert.equal(replay.findings.length, 1);
  for (const bad of ['{', 'null', '[]', '{"type":"unknown"}']) assert.equal(parsePipelineEvent(bad), null);
});

test('redirects cannot leave this origin', () => {
  for (const target of ['//evil.example', '/\\evil.example', 'https://evil.example',
    '/\n/evil.example', '/\t/evil.example', '/\r\\evil.example', null]) {
    assert.equal(safeRedirect(target), null);
  }
  assert.equal(safeRedirect('/owner/onboarding'), '/owner/onboarding');
});

test('upload UI allows only formats the backend supports', () => {
  assert.equal(MAX_UPLOAD_BYTES, 10 * 1024 * 1024);
  assert.equal(looksReadable({type: 'application/pdf', name: 'boq.pdf'}), true);
  assert.equal(looksReadable({type: '', name: 'site.PNG'}), true);
  for (const name of ['boq.xlsx', 'boq.csv', 'script.svg']) {
    assert.equal(looksReadable({type: '', name}), false);
  }
  assert.equal(looksReadable({type: 'text/html', name: 'boq.pdf'}), false);
});