import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import {
  SNAPSHOT_PATH, CANDIDATE_LINEAGE_PATH, validatePublicSnapshot,
  validatePublicJsonl, loadReadOnlyPortal
} from '../src/publicDataSource.mjs';

const snapshot = JSON.parse(await readFile(new URL('../../fixtures/snapshot.mock.json', import.meta.url), 'utf8'));
const jsonl = await readFile(new URL('./fixtures/lineage.mock.jsonl', import.meta.url), 'utf8');
const copy = (v) => structuredClone(v);

function staticFetch(s = snapshot, l = jsonl, requests = []) {
  return async (path, init) => {
    requests.push({ path, init });
    if (path === SNAPSHOT_PATH) return { ok: true, status: 200, json: async () => s };
    if (path === CANDIDATE_LINEAGE_PATH && l !== null) {
      return { ok: true, status: 200, text: async () => l };
    }
    return { ok: false, status: 404 };
  };
}

test('consumes existing frozen P0 MOCK fixture without rewriting its schema', () => {
  assert.equal(validatePublicSnapshot(snapshot).schema_version, 'portal.snapshot.v1');
  assert.match(snapshot.mock_notice, /MOCK ONLY/);
});

test('reads two first-party mock OpenLineage events and preserves column facet', async () => {
  const requests = [];
  const result = await loadReadOnlyPortal({ fetcher: staticFetch(snapshot, jsonl, requests) });
  assert.equal(result.status, 'ready');
  assert.equal(result.dataOrigin, 'MOCK');
  assert.equal(result.lineageProvenance, 'MOCK');
  assert.equal(result.lastSuccessAt, snapshot.last_success_at);
  assert.equal(result.events.length, 2);
  assert.match(result.notice, /MOCK ONLY/);
  assert.equal(validatePublicJsonl(result.lineageText).columnLineageCount, 2);
  assert.equal(result.events[0].outputs[0].facets.columnLineage.fields.birth_date.inputFields[0].field, 'BIRTHDATE');
  assert.deepEqual(requests.map((r) => r.path), [SNAPSHOT_PATH, CANDIDATE_LINEAGE_PATH]);
  assert.ok(requests.every(({init}) => init.method === 'GET' && init.credentials === 'omit'));
});

test('JSONL is only a candidate, not automatically verified by P0 summary evidence', async () => {
  const s = copy(snapshot);
  s.data_origin = 'VERIFIED_EXPORT';
  delete s.mock_notice;
  s.evidence = {
    source_commit_sha: 'a'.repeat(40),
    source_manifest_sha256: 'b'.repeat(64),
    verification_run_url: 'https://github.com/acme/healthcare/actions/runs/123'
  };
  const result = await loadReadOnlyPortal({ fetcher: staticFetch(s) });
  assert.equal(result.status, 'ready');
  assert.equal(result.dataOrigin, 'VERIFIED_EXPORT');
  assert.equal(result.lineageProvenance, 'UNVERIFIED_CANDIDATE');
  assert.match(result.warning, /not independently paired/);
  assert.equal(result.notice, null);
});

test('rejects fake VERIFIED claims without manifest evidence', async () => {
  const s = copy(snapshot);
  s.data_origin = 'VERIFIED_EXPORT';
  delete s.mock_notice;
  const result = await loadReadOnlyPortal({ fetcher: staticFetch(s) });
  assert.equal(result.status, 'unavailable');
  assert.match(result.warning, /verification evidence/);
});

test('empty OpenLineage asset is an honest no-graph result', async () => {
  const result = await loadReadOnlyPortal({ fetcher: staticFetch(snapshot, '\n') });
  assert.equal(result.status, 'empty');
  assert.equal(result.events.length, 0);
  assert.equal(result.snapshot.snapshot_id, snapshot.snapshot_id);
});

test('missing JSONL does not lose last-successful summary', async () => {
  const result = await loadReadOnlyPortal({ fetcher: staticFetch(snapshot, null) });
  assert.equal(result.status, 'summary-only');
  assert.equal(result.lastSuccessAt, snapshot.last_success_at);
  assert.match(result.warning, /missing or invalid/);
});

test('invalid JSONL fails closed and does not manufacture edges', async () => {
  const broken = jsonl + '{broken json}\n';
  const result = await loadReadOnlyPortal({ fetcher: staticFetch(snapshot, broken) });
  assert.equal(result.status, 'summary-only');
  assert.deepEqual(result.events, []);
});

test('upstream parser-required inputs/outputs must be actual arrays', () => {
  const event = JSON.parse(jsonl.split('\n')[0]);
  delete event.inputs;
  assert.throws(() => validatePublicJsonl(JSON.stringify(event)), /dataset arrays/);
});

test('rejects unapproved private facets such as SQL or run properties', () => {
  const e = JSON.parse(jsonl.split('\n')[0]);
  e.job.facets.sql = { query: 'select secret from internal' };
  assert.throws(() => validatePublicJsonl(JSON.stringify(e)), /unapproved field: sql/);
  delete e.job.facets.sql;
  e.run.facets = { spark_properties: { private: 'never publish' } };
  assert.throws(() => validatePublicJsonl(JSON.stringify(e)), /unapproved field: facets/);
});

test('failing public GET keeps previous loaded success in memory, marked stale', async () => {
  const previous = await loadReadOnlyPortal({ fetcher: staticFetch() });
  const fetcher = async () => { throw new Error('offline'); };
  const result = await loadReadOnlyPortal({ fetcher, previous });
  assert.equal(result.status, 'ready');
  assert.equal(result.stale, true);
  assert.equal(result.lastSuccessAt, snapshot.last_success_at);
  assert.match(result.warning, /previously loaded success/);
});

test('cannot reuse a different snapshot JSONL when current lineage asset is missing', async () => {
  const previous = await loadReadOnlyPortal({ fetcher: staticFetch() });
  const changed = copy(snapshot);
  changed.snapshot_id = 'snapshot-mock-next-002';
  const result = await loadReadOnlyPortal({ fetcher: staticFetch(changed, null), previous });
  assert.equal(result.status, 'summary-only');
  assert.equal(result.snapshot.snapshot_id, 'snapshot-mock-next-002');
  assert.equal(result.events.length, 0);
});

test('same snapshot retains previous validated graph when JSONL read fails', async () => {
  const previous = await loadReadOnlyPortal({ fetcher: staticFetch() });
  const result = await loadReadOnlyPortal({ fetcher: staticFetch(snapshot, null), previous });
  assert.equal(result.status, 'ready');
  assert.equal(result.stale, true);
  assert.equal(result.events.length, 2);
  assert.match(result.warning, /previously loaded static success/);
});

test('oversized candidate JSONL is rejected', () => {
  assert.throws(() => validatePublicJsonl('x'.repeat(2_000_001)), /oversized/);
});
