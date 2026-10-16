# Project scripts

Utility scripts supporting **data preparation, exploratory checks, repeatable verification, and earlier development milestones**.

## Contents

| Folder | Contents |
| --- | --- |
| [`task001/`](task001/) | Source intake, CSV and landing checks |
| [`task002/`](task002/) | Person mapping and consistency checks |
| [`task003/`](task003/) | Visit processing and verification |
| [`task004/`](task004/) | Independent generation and Person/Visit pipeline utilities |
| [`quality/`](quality/) | Repository quality and naming checks |

The Task-numbered folders are retained historical implementation files. New scripts are organized by **what the component does**, rather than a task identifier.

Some scripts inspect data while others can modify Kubernetes, object storage, or PostgreSQL. For the intended scope of a specific script, read that script and its relevant [operations documentation](../documents/operations/README.md).

[Back to the project overview](../README.md).
