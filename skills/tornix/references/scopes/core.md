# Core commands (top-level)

Top-level `tornix` commands — auth, config, data proxy, projects, tasks, file, meetings, deep-research.

> **Profile-scoped config:** on multi-profile hosts, use `HERMES_HOME` or an explicit
> profile-specific `TORNIX_CONFIG`; never use a shared/default config. Stop if neither is available.
> **Caller and organization safety:** before the first data request in each session, run
> `tornix auth whoami --json` and `tornix config show --json`; list memberships with
> `tornix api organizations list --json`. Verify a configured `org_id` is in those memberships.
> If it is absent, use only one explicit profile-to-org mapping and verify that membership;
> if none or ambiguous, stop; never guess or choose the first org.
> `whoami` is the only allowed `tornix auth` command. Never invoke login/logout/keys.
> Password-bearing account creation, password reset, account and connected-mailbox deletion, and import commands are human-only and withheld;
> never pass passwords via command options or `--data`.
> `config show` is safe (it reveals `has_key`, not the key); never inspect raw config files or `.env`.

- `tornix approvals approve --json` — Approve a workflow step.
- `tornix approvals get --json` — Get an approval request by id.
- `tornix approvals list --json` — List approval requests by status.
- `tornix approvals reject --json` — Reject a workflow step.
- `tornix auth whoami --json` — Show the authenticated user.
- `tornix calendar create --json` — Schedule a meeting: calendar entry + video room + invitations.
- `tornix calendar delete --json` — Cancel a meeting you created.
- `tornix calendar invite --json` — Add people to a meeting you created (and notify them).
- `tornix calendar list --json` — Your meetings in a window — yours AND ones you were invited to.
- `tornix calendar members --json` — People you can invite (this org's members).
- `tornix calendar show --json` — One meeting you created, with its attendees.
- `tornix calendar uninvite --json` — Remove people from a meeting you created.
- `tornix calendar update --json` — Retitle or reschedule a meeting you created.
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
- `tornix file upload --json` — Upload a local file to a project's File Center.
- `tornix gen --json` — Refresh the pinned OpenAPI snapshot from a backend.
- `tornix meetings action-items --json` — Get a meeting's action items.
- `tornix meetings get --json` — Get a meeting by id.
- `tornix meetings list --json` — List meetings (optionally by project).
- `tornix meetings minutes --json` — Get a meeting's minutes.
- `tornix meetings room-create --json` — Create a meeting (video) room in the org.
- `tornix meetings room-delete --json` — Deactivate/delete a meeting (video) room.
- `tornix meetings room-list --json` — List active meeting (video) rooms in the org.
- `tornix meetings transcript --json` — Get a meeting's transcript.
- `tornix projects create --json` — Create a project.
- `tornix projects get --json` — Get a project by id.
- `tornix projects health --json` — Get a project's health summary.
- `tornix projects list --json` — List YOUR projects (the ones you are a member of). Add --all for every project in the organization.
- `tornix projects members --json` — List a project's members.
- `tornix projects update --json` — Update a project (PUT) with a JSON body.
- `tornix rpc --json` — Call a backend RPC function.
- `tornix skill --json` — Generate the agent SKILL.md from the live command catalog.
- `tornix tasks comment --json` — Add a comment to a task.
- `tornix tasks create --json` — Create a task in a project.
- `tornix tasks get --json` — Get a task by id.
- `tornix tasks list --json` — List tasks in a project.
- `tornix tasks update --json` — Update a task (PUT) with a JSON body.
- `tornix workload calendar --json` — Resource calendar: person × day — capacity, hours booked, leave, holidays (≤ 6 weeks).
- `tornix workload check --json` — Before assigning: each person's load in the task window before → after, leave, first free slot, alternatives. Writes nothing.
- `tornix workload person --json` — One person's Workload and open tasks with their remaining hours.
- `tornix workload preview --json` — What moving tasks WOULD do (before → after, warnings). Writes nothing.
- `tornix workload requests --json` — Assignment requests: asked of me (inbox) or that I asked (outbox).
- `tornix workload sprint-preview --json` — Who would take each unassigned sprint item (balanced / round robin) — a preview, writes nothing.
- `tornix workload suggestions --json` — The engine's own rebalancing suggestions (Team insights) — who, which task, to whom, why.
- `tornix workload team --json` — Every person's Workload the caller may see (admin: org; PM: their projects).

(55 available commands; auth and credential lifecycle operations withheld)
