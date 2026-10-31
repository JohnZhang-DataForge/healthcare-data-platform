# Shared Data Engine — first offline release

The only new Python package is `healthcare_data_engine`, version **0.1.0**. It contains platform-neutral FHIR R4 Patient/Encounter normalization, Local v1 Contract validation, pure replay decisions and lazy PySpark DataFrame schema building.

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

Build the sole wheel (`--no-build-isolation` uses pinned build tools already present):

```sh
.venv-shared/bin/python -m pip wheel --no-index --no-deps --no-build-isolation --wheel-dir dist ./shared-data-engine
sha256sum dist/*.whl
.venv-shared/bin/pip install --no-index --no-deps --force-reinstall dist/healthcare_data_engine-0.1.0-*.whl
```

The GitHub-hosted CI prepares its dependency wheelhouse, **installs the test environment without the index**, verifies PySpark rows/schema, builds the wheel, then verifies installed import from outside the checkout. CI artifacts include the wheel and SHA256. A green CI result proves **offline synthetic tests**, not Fabric Environment Publish/Notebook execution, Fabric Runtime compatibility or Silver APPROVED.
