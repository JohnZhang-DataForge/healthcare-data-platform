# Self-Runner cross-repo workflow dependency inventory (123/123 source scan)

> **PINNED STATIC REVIEW / NO WORKFLOW DISPATCH**. Self-Runner Main `ffd0eccecbf0148183b956e6e4416d4b8d99002b`, Healthcare Main `ea2d2e5ffd98c529c79626c7c926828a32fb7a7b`. These are **distinct SHA baselines**. A legacy root-relative path is potentially **correct** when checkout is explicitly pinned to a pre-move commit. It is **wrong** only if the workflow actually checks out the new tree or uses a runtime context that expects the new tree.

This scans **all 123 tracked `.github/workflows/*.yml` in Self-Runner** for literal checkout references, root-prefixed sources, execution risk flags and trigger hints; does **not** follow reusable scripts, indirect calls, Helm values or real runtime config. No inference of safe retirement solely from fixed SHA or one particular event type.

| # | Self-Runner Workflow source | Blob SHA | Healthcare checkout ref(s) | Old source path references | New source path references | Trigger hints | Resource side-effect hints | Review disposition |
| ---: | --- | --- | --- | ---: | ---: | --- | --- | --- |
