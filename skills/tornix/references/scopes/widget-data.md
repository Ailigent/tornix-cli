# `tornix api widget-data` — 3 commands

- `tornix api widget-data get --json` — Fetch up to N sample rows for a data source. Service-key auth only — used by the project-health widget builder to give the AI ground-truth shape before Phase B.
- `tornix api widget-data widget-data-get --json` — Execute a data source and return its rows
- `tornix api widget-data widget-schema --json` — Enumerate data sources + their schemas. Public: no per-user data — catalog metadata only; consumed by the project-health widget builder at boot.

(3 commands)
