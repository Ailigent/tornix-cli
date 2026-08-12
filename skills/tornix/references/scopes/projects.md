# `tornix api projects` — 9 commands

- `tornix api projects delete --json` — Delete project (cascades to all child records, scoped to the caller org)
- `tornix api projects get --json` — Get project by ID
- `tornix api projects health --json` — Get project health snapshot
- `tornix api projects list --json` — List projects in organization
- `tornix api projects members --json` — List project members
- `tornix api projects members-create --json` — Assign a member (e.g. the PM) to a project, upserting on (project_id, user_id)
- `tornix api projects replace --json` — Update project
- `tornix api projects sections --json` — List project sections
- `tornix api projects sync-boundaries --json` — Ensure auto project start/end milestones exist (derived from the schedule)

(9 commands)
