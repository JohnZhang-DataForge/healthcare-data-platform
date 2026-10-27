/**
 * First-party, read-only public asset adapter. No dependency on Marquito source.
 *
 * JSONL endpoint is PROPOSED, not part of frozen P0. Coordinator + Agent B must
 * approve it before publish. The caller may pass validated .lineageText to a
 * separately licensed Marquito parseLineageText() in a later integration.
 */
export const SNAPSHOT_PATH = '/data/latest.json';
export const CANDIDATE_LINEAGE_PATH = '/data/lineage/latest.jsonl';
const MAX_JSONL_BYTES = 2_000_000;

const isObject = (v) => v !== null && typeof v === 'object' && !Array.isArray(v);
const nonempty = (v) => typeof v === 'string' && v.trim().length > 0;
const isTime = (s) => nonempty(s) && Number.isFinite(Date.parse(s));
const sha = (value, size) => typeof value === 'string' &&
  new RegExp('^[a-f0-9]{' + size + '}$').test(value);

function keysOnly(value, allowed, where) {
  if (!isObject(value)) throw new Error(where + ' must be an object');
  for (const key of Object.keys(value)) {
    if (!allowed.includes(key)) throw new Error(where + ' has unapproved field: ' + key);
  }
}

/** A defensive minimum; full schema ownership remains with P0. */
export function validatePublicSnapshot(snapshot) {
  if (!isObject(snapshot) || snapshot.schema_version !== 'portal.snapshot.v1') {
    throw new Error('Unsupported public snapshot schema');
  }
  if (!nonempty(snapshot.snapshot_id) || !isTime(snapshot.last_success_at) ||
      !isTime(snapshot.generated_at) || !isObject(snapshot.summary) ||
      !Array.isArray(snapshot.runs) || !Array.isArray(snapshot.datasets) ||
      !Array.isArray(snapshot.hospitals) || !isObject(snapshot.lineage)) {
    throw new Error('Invalid public snapshot summary');
  }
  if (snapshot.data_origin === 'MOCK') {
    if (!nonempty(snapshot.mock_notice) || snapshot.mock_notice.length < 12 ||
        'evidence' in snapshot) {
      throw new Error('MOCK requires a visible notice and no verified evidence');
    }
  } else if (snapshot.data_origin === 'VERIFIED_EXPORT') {
    const e = snapshot.evidence;
    if (!isObject(e) || !sha(e.source_commit_sha, 40) ||
        !sha(e.source_manifest_sha256, 64) ||
        !/^https:\/\/github\.com\/[\w.-]+\/[\w.-]+\/actions\/runs\/\d+$/.test(e.verification_run_url) ||
        'mock_notice' in snapshot) {
      throw new Error('VERIFIED_EXPORT requires P0 verification evidence');
    }
  } else {
    throw new Error('Unknown public data origin');
  }
  return snapshot;
}

const EVENT_FIELDS = ['eventType', 'eventTime', 'producer', 'schemaURL', 'run', 'job', 'inputs', 'outputs'];
const JOB_FIELDS = ['namespace', 'name', 'facets'];
const DATASET_FIELDS = ['namespace', 'name', 'facets'];
const COLUMN_FIELD_FIELDS = ['inputFields', 'transformationType', 'transformationDescription'];
const FIELD_INPUT_FIELDS = ['namespace', 'name', 'field', 'transformations'];
const TRANSFORM_FIELDS = ['type', 'subtype', 'description', 'masking'];

function validateDataset(ds) {
  keysOnly(ds, DATASET_FIELDS, 'dataset');
  if (!nonempty(ds.namespace) || !nonempty(ds.name)) throw new Error('Dataset identity missing');
  if (ds.facets === undefined) return;
  keysOnly(ds.facets, ['schema', 'columnLineage'], 'dataset facets');
  if (ds.facets.schema !== undefined) {
    keysOnly(ds.facets.schema, ['fields'], 'schema facet');
    if (!Array.isArray(ds.facets.schema.fields)) throw new Error('Invalid schema fields');
    for (const field of ds.facets.schema.fields) {
      keysOnly(field, ['name', 'type'], 'schema field');
      if (!nonempty(field.name) || !nonempty(field.type)) throw new Error('Invalid schema field');
    }
  }
  if (ds.facets.columnLineage !== undefined) {
    keysOnly(ds.facets.columnLineage, ['fields'], 'column lineage facet');
    if (!isObject(ds.facets.columnLineage.fields)) throw new Error('Invalid column lineage fields');
    for (const [target, entry] of Object.entries(ds.facets.columnLineage.fields)) {
      if (!nonempty(target)) throw new Error('Missing target column');
      keysOnly(entry, COLUMN_FIELD_FIELDS, 'target column');
      if (!Array.isArray(entry.inputFields)) throw new Error('Invalid inputFields');
      for (const source of entry.inputFields) {
        keysOnly(source, FIELD_INPUT_FIELDS, 'input column');
        if (!nonempty(source.namespace) || !nonempty(source.name) || !nonempty(source.field)) {
          throw new Error('Invalid column source identity');
        }
        if (source.transformations !== undefined) {
          if (!Array.isArray(source.transformations)) throw new Error('Invalid transformations');
          for (const item of source.transformations) keysOnly(item, TRANSFORM_FIELDS, 'transformation');
        }
      }
    }
  }
}

/**
 * Preserves original JSONL text for an authorized upstream parser; this DOES
 * NOT replace Exporter's pre-publication PHI / URI / SQL redaction review.
 */
export function validatePublicJsonl(text) {
  if (typeof text !== 'string' || text.length > MAX_JSONL_BYTES) {
    throw new Error('Invalid or oversized static JSONL');
  }
  const lines = text.split(/\r?\n/).filter((s) => s.trim());
  const events = lines.map((line, index) => {
    let event;
    try { event = JSON.parse(line); }
    catch { throw new Error('Invalid JSONL at line ' + (index + 1)); }
    keysOnly(event, EVENT_FIELDS, 'event');
    if (!['START', 'COMPLETE', 'FAIL', 'ABORT', 'OTHER', 'RUNNING'].includes(event.eventType) ||
        !isTime(event.eventTime) || !nonempty(event.producer) ||
        !nonempty(event.schemaURL)) throw new Error('Invalid event header at line ' + (index + 1));
    keysOnly(event.run, ['runId'], 'run');
    keysOnly(event.job, JOB_FIELDS, 'job');
    if (!nonempty(event.run.runId) || !nonempty(event.job.namespace) ||
        !nonempty(event.job.name) || !Array.isArray(event.inputs) ||
        !Array.isArray(event.outputs)) throw new Error('Invalid event identity or dataset arrays');
    if (event.job.facets !== undefined) {
      keysOnly(event.job.facets, ['jobType'], 'job facets');
      if (event.job.facets.jobType !== undefined) {
        keysOnly(event.job.facets.jobType, ['jobType', 'processingType', 'integration'], 'job type facet');
      }
    }
    for (const ds of [...event.inputs, ...event.outputs]) validateDataset(ds);
    return event;
  });
  const columnLineageCount = events.reduce((count, event) => count +
    event.outputs.reduce((total, ds) => total +
      Object.values(ds.facets?.columnLineage?.fields || {}).reduce(
        (n, f) => n + f.inputFields.length, 0), 0), 0);
  return { events, lineageText: text, eventCount: events.length, columnLineageCount };
}

async function getStatic(fetcher, path) {
  const response = await fetcher(path, { method: 'GET', credentials: 'omit', redirect: 'error', cache: 'no-store' });
  if (!response || !response.ok) {
    throw new Error('Static resource unavailable: ' + path + ' (' + (response?.status ?? 'network') + ')');
  }
  return response;
}

function unavailable(error) {
  return { status: 'unavailable', snapshot: null, events: [], lineageText: '',
    stale: false, lastSuccessAt: null, dataOrigin: null,
    lineageProvenance: 'NONE', notice: null, warning: error.message };
}

/**
 * Returns a display model, never initiates an action. previous is ephemeral
 * in-memory last-success state; we do not persist raw lineage in localStorage.
 */
export async function loadReadOnlyPortal({ fetcher = globalThis.fetch, previous = null } = {}) {
  let snapshot;
  try {
    snapshot = validatePublicSnapshot(await (await getStatic(fetcher, SNAPSHOT_PATH)).json());
  } catch (error) {
    return previous?.snapshot
      ? { ...previous, stale: true, warning: 'Unable to refresh public snapshot; showing previously loaded success.' }
      : unavailable(error);
  }

  const base = {
    status: 'summary-only', snapshot, events: [], lineageText: '', stale: false,
    lastSuccessAt: snapshot.last_success_at, dataOrigin: snapshot.data_origin,
    notice: snapshot.data_origin === 'MOCK' ? snapshot.mock_notice : null,
    lineageProvenance: 'NONE', warning: null,
  };
  try {
    const text = await (await getStatic(fetcher, CANDIDATE_LINEAGE_PATH)).text();
    const lineage = validatePublicJsonl(text);
    if (lineage.eventCount === 0) {
      return { ...base, status: 'empty', warning: 'No published OpenLineage events; graph unavailable.' };
    }
    return {
      ...base, status: 'ready', events: lineage.events, lineageText: lineage.lineageText,
      lineageProvenance: snapshot.data_origin === 'MOCK' ? 'MOCK' : 'UNVERIFIED_CANDIDATE',
      warning: snapshot.data_origin === 'MOCK'
        ? null
        : 'Lineage JSONL is not independently paired to the VERIFIED_EXPORT snapshot yet.',
    };
  } catch {
    if (previous?.snapshot?.snapshot_id === snapshot.snapshot_id && previous.status === 'ready') {
      return { ...previous, stale: true, warning: 'Lineage refresh failed; showing previously loaded static success.' };
    }
    return { ...base, warning: 'Lineage JSONL missing or invalid; last successful summary remains available.' };
  }
}
