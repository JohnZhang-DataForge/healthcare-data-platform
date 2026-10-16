# Tests

Python test suites for the platform's **source contracts, batch handling, transformations, writer behavior, and repository quality checks**.

## Test areas

| Folder | Focus |
| --- | --- |
| [`synthea_new_only/`](synthea_new_only/) | Independent generator and publication contracts |
| [`landing_discovery/`](landing_discovery/) | READY manifest discovery and batch routing |
| [`landing_claim/`](landing_claim/) | Claim, state, and fencing behavior |
| [`omop_writer/`](omop_writer/) | Writer validation, commit preparation, and replay safeguards |
| [`quality/`](quality/) | Source code organization checks |
| [`task001/`](task001/), [`task002/`](task002/), [`task003/`](task003/), [`task004/`](task004/) | Historical milestone test suites |

These tests provide local or CI evidence for specific code paths. Successful unit tests do not, by themselves, establish that an Airflow job or PostgreSQL transaction succeeded in the lab.

See [testing and evidence](../documents/development/TESTING-AND-EVIDENCE.md) and [CI workflows](../.github/README.md).
