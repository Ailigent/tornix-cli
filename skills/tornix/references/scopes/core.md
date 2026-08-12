# Core commands (top-level)

Top-level `tornix` commands — auth, config, data proxy, projects, tasks, file, meetings, deep-research.

- `tornix approvals approve --json` — Approve a workflow step.
- `tornix approvals get --json` — Get an approval request by id.
- `tornix approvals list --json` — List approval requests by status.
- `tornix approvals reject --json` — Reject a workflow step.
- `tornix auth keys create --json` — Create a new API key (raw key shown once).
- `tornix auth keys delete --json` — Delete an API key by id.
- `tornix auth keys get --json` — Show one API key by id.
- `tornix auth keys list --json` — List your API keys.
- `tornix auth keys revoke --json` — Revoke an API key by id.
- `tornix auth keys scopes --json` — List available permission scopes.
- `tornix auth keys update --json` — Update an API key (PATCH) with a JSON body.
- `tornix auth keys usage --json` — Show usage statistics for an API key.
- `tornix auth login --json` — Authenticate with an API key or email/password. Prefer TORNIX_API_KEY env over --api-key (which is visible in the process list and shell history).
- `tornix auth logout --json` — Clear the stored API key / token.
- `tornix auth whoami --json` — Show the authenticated user.
- `tornix catalog --json` — Print the full command tree (use --json for agents).
- `tornix config get --json` — Print a single config value.
- `tornix config org --json` — Set and persist the active organization id.
- `tornix config set --json` — Set and persist a config value.
- `tornix config show --json` — Show the active configuration.
- `tornix data delete --json` — Delete rows matching --eq filters.
- `tornix data insert --json` — Insert a row (or array of rows) into a table.
- `tornix data select --json` — Read rows from a table with optional filters.
- `tornix data update --json` — Update rows matching --eq filters.
- `tornix deep-research --json` — Multi-source research over PMO data and/or the web.
- `tornix doctor --json` — Diff the pinned OpenAPI snapshot against a live backend. Exits non-zero on drift, so CI can gate on it.
- `tornix gen --json` — Refresh the pinned OpenAPI snapshot from a backend.
- `tornix meetings action-items --json` — Get a meeting's action items.
- `tornix meetings get --json` — Get a meeting by id.
- `tornix meetings list --json` — List meetings (optionally by project).
- `tornix meetings minutes --json` — Get a meeting's minutes.
- `tornix meetings transcript --json` — Get a meeting's transcript.
- `tornix projects create --json` — Create a project.
- `tornix projects get --json` — Get a project by id.
- `tornix projects health --json` — Get a project's health summary.
- `tornix projects list --json` — List projects in the active organization.
- `tornix projects members --json` — List a project's members.
- `tornix projects update --json` — Update a project (PUT) with a JSON body.
- `tornix rpc --json` — Call a backend RPC function.
- `tornix skill --json` — Generate the agent SKILL.md from the live command catalog.
- `tornix tasks comment --json` — Add a comment to a task.
- `tornix tasks create --json` — Create a task in a project.
- `tornix tasks get --json` — Get a task by id.
- `tornix tasks list --json` — List tasks in a project.
- `tornix tasks update --json` — Update a task (PUT) with a JSON body.

(45 commands)
