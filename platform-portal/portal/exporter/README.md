# Marquez read-only exporter

**State:** offline implementation only. No local Marquez readback, public staging,
or Azure end-to-end verification has been performed for this branch.

## Why the raw-event endpoint

Marquez exposes GET \`/api/v1/events/lineage\`, returning its stored OpenLineage
\`events\` with \`totalCount\`. This is more faithful than reverse-engineering a
RunEvent from Marquez's derived Job/Run/Dataset graph. The exporter requests pages
in ascending order and refuses inconsistent or truncated responses. It does **not**
use POST/PATCH/PUT/DELETE; no Writer, Synthea, PG14, Cloudflare, or Azure calls exist.

\`marquez_exporter.py\` conservatively reconstructs **public-safe OpenLineage
RunEvent records** from GET response fields: event type/time, the real Job
namespace/name, real Run ID, real Dataset namespace/name, schema field names/types,
and explicit \`columnLineage.fields[*].inputFields\`. Run arguments, SQL, Job/Run
facets, unknown Dataset facets, transformation expressions, and arbitrary metadata
are not exported. OpenLineage producer points to the exporter; this sanitized
JSONL is **not a byte-identical source-event archive**. The frontend parser
\`projects/marquito/src/lib/parseLineage.ts\` requires
\`eventType/job/run/inputs/outputs\` and reads \`schema\` and \`columnLineage\` facets.
The candidate static URL is \`/data/lineage/latest.jsonl\` (Agent A/Coordinator
compatibility review pending); snapshot remains \`/data/latest.json\`.

If a real Dataset/Job identifier carries a secret, private URL, internal IP, or
object-store location, the exporter **fails closed rather than renaming it**.
This intentionally blocks some real workloads until the owner approves an
identity-preserving public representation. Synthea business column names remain
visible when they are safe; no patient records are included. A column link is
only accepted if its source Dataset appears in the same RunEvent's inputs. No
cross-platform Dataset equivalence is inferred from similar names.

## Offline staging

From repository root:

\`\`\`bash
python platform-portal/portal/exporter/marquez_exporter.py \
  --marquez-url http://<internal-marquez-host>:5000/api/v1 \
  --output /tmp/portal-export-candidate-unique
\`\`\`

The URL is an example only: **do not run against shared Marquez until separately
authorized**. The default result is a new local-only
\`lineage.candidate.jsonl\` and \`audit.json\`, with status \`CANDIDATE_ONLY\`.
There is **no** \`data/latest.json\` without evidence.

To stage a possibly publishable bundle, provide **actual immutable source
manifest bytes** plus a separately obtained, externally reviewed evidence JSON:

\`\`\`bash
python platform-portal/portal/exporter/marquez_exporter.py \
  --marquez-url http://<internal-marquez-host>:5000/api/v1 \
  --manifest /secure/readback/manifest.json \
  --evidence /secure/readback/verified-evidence.json \
  --output /tmp/portal-verified-unique
\`\`\`

Evidence structure (values are *placeholders*, not acceptable runtime proof):

\`\`\`json
{
  "source_commit_sha": "<40-digit-actual-source-commit>",
  "source_manifest_sha256": "<sha256-of-exact-manifest-bytes>",
  "verification_run_url": "https://github.com/ORG/REPO/actions/runs/123",
  "independent_readback": {
    "passed": true,
    "source_commit_sha": "<same-source-commit>",
    "source_manifest_sha256": "<same-manifest-sha256>",
    "verification_run_url": "https://github.com/ORG/REPO/actions/runs/123",
    "export_jsonl_sha256": "<sha256-of-sanitized-jsonl>",
    "checked_at": "2026-10-27T20:00:00Z",
    "patient_count": 0,
    "encounter_count": 0,
    "dq_checks_passed": 0,
    "dq_checks_failed": 0,
    "quality_status": "PASS",
    "source_backend": "LOCAL_K8S",
    "verified_run_ids": ["<actual-openlineage-run-id>"],
    "dataset_layers": {
      "real-namespace::actual-dataset-name": "LANDING"
    },
    "hospitals": []
  }
}
\`\`\`

All numbers, hospital identities/source types, Dataset layer classifications,
and included successful Run IDs must come from an **independent readback**,
not be computed or guessed from event names. A Run needs observed START +
COMPLETE; actual column edges come only from the source columnLineage facet.
Missing proof, bad Manifest bytes, run mismatches, failing quality, unsafe
identifiers, or broken links block staging. The v1 JSON Schema is immutable.
If \`source_backend=MIXED\`, evidence must also supply
\`independent_readback.run_backends\` mapping real Run IDs to LOCAL_K8S/FABRIC.

**Important evidence limitation:** An evidence JSON file is not a digital signature.
This offline tool validates its structure, content hashes, run references, and
cross-evidence consistency, but cannot on its own establish that a GitHub URL
really had a successful execution or that an alleged independent readback was
performed. The operator/Coordinator must independently verify the GitHub Run,
checkout SHA, data Manifest, actual source readback, and data provenance before
treating \`VERIFIED_EXPORT\` as public-acceptance proof. Never publish just
because a local fixture passed the offline gate. No real evidence was supplied
with this PR.

With structurally valid evidence, the **new staging directory** contains:

\`\`\`text
data/latest.json
data/snapshots/<snapshot_id>.json
data/lineage/latest.jsonl
audit.json
\`\`\`

The tool never overwrites an existing output directory, updates a deployed
\`latest.json\`, or deploys anything. Promotion of the staged bundle is a separate
reviewed and authorized operation by the Coordinator/user.

## Tests

\`\`\`bash
python -m pip install -r platform-portal/portal/requirements-test.txt
python -m unittest discover -s platform-portal/portal/exporter/tests \
  -p 'test_*.py' -v
\`\`\`

The tests use synthetic memory fixtures and fake GET responses. A dedicated
offline GitHub Action runs these tests without cluster or Azure credentials.
