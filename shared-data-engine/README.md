# Shared Data Engine — first offline release

The only new Python package is `healthcare_data_engine`, version **0.1.1**. It contains platform-neutral FHIR R4 Patient/Encounter normalization, Local v1 Contract validation, pure replay decisions and lazy PySpark DataFrame schema building.

## Ownership and Contract

- Canonical authority remains `../local-data-platform/spark/contracts/canonical/{patient-v1,encounter-v1}.json`. No copied schema is packaged.
- The caller supplies **original source bytes**, expected SHA256/size and explicit `BatchContext`. The caller loads the exact pinned Local contract bytes and injects the resulting dict to the mapper.
- `parse_fhir_resources` returns accepted resources and rejected malformed or conflicting resources. Each `normalize_fhir_*` returns accepted rows, quarantined v1-incompatible records and rejects; platform readback must also check accepted Patient/Encounter FKs.
- When Local v1 cannot represent a valid FHIR optional or multi-valued clinical field, quarantine instead of inventing defaults. Canonical v2 needs a separate decision.
- There is no Blob/S3/OneLake/Delta/PG driver, SparkSession constructor or cloud publisher here.

## Offline testing

Use Python 3.11 and Java 17. Install exact test dependencies from `requirements-test.txt`. To prepare an offline wheelhouse **on the same OS/Python architecture**:

```sh
python -m pip wheel --wheel-dir wheelhouse -r shared-data-engine/requirements-test.txt
python -m venv .venv-shared
.venv-shared/bin/pip install --no-index --find-links=wheelhouse -r shared-data-engine/requirements-test.txt
.venv-shared/bin/python -m unittest discover -s shared-data-engine/tests -p 'test_*.py' -v
```

To make the sole wheel reproducible, set `SOURCE_DATE_EPOCH=1704067200` consistently for each build. CI rebuilds the identical source twice and requires byte-for-byte equality with `cmp`.

Build the sole wheel (`--no-build-isolation` uses pinned build tools already present):

```sh
SOURCE_DATE_EPOCH=1704067200 .venv-shared/bin/python -m pip wheel --no-index --no-deps --no-build-isolation --wheel-dir dist ./shared-data-engine
sha256sum dist/*.whl
.venv-shared/bin/pip install --no-index --no-deps --force-reinstall dist/healthcare_data_engine-0.1.1-*.whl
```

The GitHub-hosted CI prepares its dependency wheelhouse, **installs the test environment without the index**, verifies PySpark rows/schema, builds the wheel, then verifies installed import from outside the checkout. CI artifacts include the wheel and SHA256. For Fabric Runtime 2.0 the current target is Python 3.13 / PySpark 4.1.1 / Java 21.
The separate GitHub-hosted CI job validates both the pure Python 3.13 API and Spark
4.1 DataFrame behavior, then builds and installs the wheel in a Python 3.13
environment. The versioned package retains Python 3.11 / PySpark 3.5.7
compatibility for existing Local workloads; the optional `spark` extras are
selected by interpreter version. Never force-install old `0.1.0` metadata in
Fabric Runtime 2.0 or consider the new `0.1.1` installed until actual
Environment staging/Publish/binding and safe runtime import are verified.

A green CI result proves **offline synthetic compatibility/build/install only**,
not Fabric Environment Publish, Notebook execution, or Silver APPROVED.
