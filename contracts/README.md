# Data contracts

This folder contains **machine-readable contracts** describing source file layouts, batch identities, publication requirements, and writer input expectations.

## Contents

- [`synthea/`](synthea/) — source CSV schemas, producer identity, and READY-publication agreements
- [`omop-writer/`](omop-writer/) — writer-facing batch identity contract

These JSON definitions help different parts of the pipeline agree on the format and meaning of a batch. They do not contain the clinical data itself.

See [Python applications](../apps/README.md), [Spark processing](../spark/README.md), and the [landing component](../documents/components/landing/README.md).
