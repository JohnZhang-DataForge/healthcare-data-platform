# Synthea source producer

Synthea creates **synthetic clinical data** for the Healthcare Data Platform. The independent NEW_ONLY producer generates a batch, validates its files, and publishes a finalized manifest for downstream use.

Generation is separate from Airflow's batch consumption. Additional source update/mixed-data modes remain outside the demonstrated NEW_ONLY scope.

**Related material**

- [Producer Python code](../../../apps/synthea/)
- [Producer image definitions](../../../images/synthea-new-only/)
- [Source contracts](../../../contracts/README.md)
- [Landing and batch identity](../landing/README.md)

[All components](../README.md).
