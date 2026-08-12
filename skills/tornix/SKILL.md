---
name: tornix
description: Drive the Tornix PMO platform (app.tornix.ai) from the CLI — projects, tasks, procurement, approvals, risks, cost, meetings, AI, and deep-research. Every command supports --json.
---

# Tornix CLI Skill

`tornix` is an agent-native CLI for the Tornix PMO backend. **Always pass `--json`**
for machine-readable output (it works before or after any subcommand).

## Authentication
Auth is ALREADY configured on the machine — do NOT run `tornix auth login` and NEVER
ask the user for an API key. The active profile is **prod** (`https://app.tornix.ai`)
with the user's API key + org id stored in `~/.config/tornix/config.toml` (0600).
If a command fails with exit code 3 (401), tell the user the API key is
invalid/expired and needs a new one from the Tornix web app — do NOT retry or
re-authenticate. Scope a request to an org with `--org <id>` or `TORNIX_ORG`.

Discover the full surface programmatically: `tornix catalog --json`.

## User profile & discovery (MANDATORY first step)
This skill is multi-user. NEVER assume the caller is a specific person or org.
At the start of every session:
1. `tornix auth whoami --json` → the caller's user id + email.
2. Load the matching profile: `skill_view(name='tornix', file_path='profiles/<email>.md')`.
   - If it exists → use its ids (user id, org, default project, team) for everything.
   - If it does NOT exist → **bootstrap**: run `tornix api organizations list --json`
     (orgs), `tornix projects list --json` (projects), `tornix api projects members
     <project-id> --json` (team user_ids), then create `profiles/<email>.md` from
     `profiles/_template.md` and fill it. Ask the user to confirm the default project.
3. When the user names a project/team member, resolve ids from the profile — never
   guess or hardcode. If an id is missing from the profile, discover it live
   (`tornix projects list`, `tornix api projects members`, `tornix api users list`)
   and update the profile.

## Conventions
- Output: add `--json` to any command. Errors go to stderr as `{"error": {...}}` with
  non-zero exit codes (3=auth, 4=not-found, 5=validation, 6=rate-limit/credits).
- Full backbone: `tornix api <tag> <operation> [--opts] --json` covers every backend operation.
- Escape hatches: `tornix data select <table> --eq col=val --json`, `tornix rpc <fn> --arg k=v --json`.
- Deep research: `tornix deep-research "<question>" --source pmo|web|both --project <id> --json`.
  Default returns a structured cited corpus for you to synthesize; add `--synthesize`
  to have Tornix AI write the report.
- Language: follow the user's language (profile.language). Egyptian Arabic + English
  is common; code/commands stay in English.

## Self-improvement loop
The skill grows from real usage. Rules:
- **Every pitfall, user correction, or discovered workflow gets a dated entry** in
  `lessons/YYYY-MM.md` (see `lessons/README.md`). Keep entries 2-4 lines.
- A lesson is **promoted** into SKILL.md once proven (applied successfully 2+ times
  or caused a user correction once). SKILL.md holds only active rules; lessons/ keeps history.
- When the backend adds scopes, regenerate: `tornix skill generate --out <path>`,
  re-apply this preamble, re-run `scripts/split_skill_scopes.py`, and note it in lessons.
- User-specific facts (ids, team, default project) belong in `profiles/`, NEVER in SKILL.md.

## Meeting (video) rooms — curated CLI commands
- **Meeting rooms live in the `video_rooms` table, NOT `chat_rooms`.** A `chat_rooms`
  row is a team chat, never a meeting room — creating one there will NOT show up in
  the Meetings tab. (Pitfall verified 2026-08-11.)
- `tornix meetings room-create --name "room name"` — creates a video room in the
  active org (name must be unique in the org; room_name follows the frontend
  convention `room-{orgId}-{ts}-{rand}`).
- `tornix meetings room-list` — list active video rooms in the org.
- `tornix meetings room-delete <room_id>` — deactivate; `--hard` deletes the row.
- These wrap `/api/v1/data/{table}` (data proxy) — the same path `tornix data`
  uses; keep using the `{table}` placeholder so the drift test passes.

## Chat rooms — team chat (NOT video meetings)
- **Chat rooms live in `chat_rooms`** (CommunicationController). Do NOT confuse with
  meeting/video rooms (`video_rooms` table — see Meeting section above).
- `tornix api chat rooms-create --data '{"name":"Home","description":"..."}' --json` → room id
  (room is created by the API-key user, who becomes OWNER).
- Add participants: `tornix api chat rooms-participants-create <room-id> --user-id <uid> --json`
  (role defaults to MEMBER). Resolve user ids from the profile or
  `tornix api chat participants <room-id> --json` (profiles carry full_name/email).

## Key workflows
- **Default project** = the profile's `default_project` — when the user doesn't name
  a project, use that one. Resolve its id from the profile.
- **NEW PROJECTS: always AGILE from the start** — the user picks the AGILE template when
  creating a project (`template_used=AGILE`). Never create a plain/waterfall project.
  If a project was created without the template, fix it via
  `api projects replace <id> --template-used AGILE` (and match the org's agile config:
  `default_sprint_length_weeks=1`, `board_mode=scrum`, `auto_close_enabled=true`).
- **TRADITIONAL (Waterfall) projects** — for client delivery projects:
  `template_used=BLANK` + `project_methodology=WATERFALL` (TRADITIONAL is NOT a valid value —
  the API rejects it; valid: CONSTRUCTION, SOFTWARE_DELIVERY, EVENT_PLANNING, MARKETING_CAMPAIGN,
  RESEARCH_THESIS, BLANK, AGILE for template; AGILE, SCRUM, KANBAN, WATERFALL, PRINCE2, HYBRID,
  LEAN, CPM, SIX_SIGMA_DMAIC for methodology). Full setup recipe:
  1. `tornix projects create --name "..." --description "..." --json` → project_id
  2. `tornix api projects replace <id> --template-used BLANK --project-methodology WATERFALL --json`
  3. **Create a section FIRST** — new projects have NO sections and `tasks create` fails with
     `Argument section is missing`. Insert: `tornix data insert project_sections --data
     '{"project_id":"<id>","name":"Backlog","position":0}' --json`
  4. Add members: `tornix api projects members-create <id> --user-id <uid> --job-title-role-id <rid> --json`
  5. Create tasks: `tornix tasks create --project <id> --title "..." --assignee <uid> --json`
     (returns task id in `task.id` or top-level `id`)
  6. Set planned dates per task: `tornix data update project_tasks --eq id=<task> --data
     '{"planned_start":"YYYY-MM-DDT00:00:00.000Z","planned_finish":"YYYY-MM-DDT23:59:59.000Z"}' --json`
     — these dates are what make tasks appear on the Gantt.
  7. Add dependencies (Finish-to-Start between phases):
     `tornix api tasks dependencies-create <target> --source-task-id <src> --target-task-id <tgt>
     --dependency-type FINISH_TO_START --json`
  8. Add milestones: `tornix data insert milestones --data '{"project_id":"<id>","stage_name":"M1 — ...",
     "start_date":"...","due_date":"...","milestone_kind":"manual","user_id":"<uid>"}' --json`
  9. Set project dates + status: `tornix api projects replace <id> --start-date "2026-08-11T00:00:00.000Z"
     --end-date "2026-11-08T23:59:59.000Z" --status ACTIVE --json` (ISO-8601 full datetime REQUIRED —
     bare dates are rejected)
  10. **Cost data**: insert `budget_items` rows (table accessible via data API):
      `tornix data insert budget_items --data '{"project_id":"<id>","category_name":"...",
      "baseline_amount":96000,"currency":"SAR","status":"DRAFT","task_id":"<task>","description":"..."}' --json`
      THEN set the same amounts on the tasks themselves (this is what the baseline/cost rollup reads):
      `tornix data update project_tasks --eq id=<task> --data '{"budgeted_cost":96000,"material_cost":96000}' --json`
      (pattern from existing projects: materials = baseline_amount). Then:
      `tornix api cost recalculate <id> --json` → "Cost roll-up completed"
      **Contingency reserve** (client standard = 10%): update each budget_items row with
      `'{"contingency": <10% of baseline>, "contingency_reserve_percentage": 10}'` via
      `tornix data update budget_items --eq id=<bid> --data ...` (same pattern as existing projects:
      contingency = baseline * pct, stored as its own field — it does NOT fold into the baseline
      total_cost, it shows as a separate reserve line in cost reports).
  11. **Baseline** (needed for EVM + Gantt variance):
      `tornix api gantt baselines --data '{"project_id":"<id>","name":"Baseline 1 — ..."}' --json`
      → returns baseline id + total_cost (verify it's non-zero after cost data).
      Then `tornix api gantt set-primary --data '{"baseline_id":"<id>","project_id":"<pid>"}' --json`,
      `tornix api gantt update-status --data '{"baseline_id":"<id>","status":"APPROVED"}' --json`,
      `tornix api gantt activate --data '{"baseline_id":"<id>","project_id":"<pid>"}' --json`.
      EVM check: `tornix api cost evm <pid> --data-date YYYY-MM-DD --json` → BAC should equal total cost.
  12. **Upload project files** (File Center attachments):
      `tornix file upload <path> --project <id> --json` → returns document_id. Repeat per file.
      Verify: `tornix api documents list --project-id <id> --json`.
  13. **Risks** (from the project's plan/scope — create 3-5 real risks):
      `tornix api risks create <pid> --title "..." --description "..." --category SCHEDULE|FINANCIAL|TECHNICAL|LEGAL
      --severity CRITICAL|MAJOR|MODERATE|MINOR --likelihood CERTAIN|LIKELY|POSSIBLE|UNLIKELY|RARE
      --status OPEN|MONITORED|MITIGATED|ESCALATED --detection-date YYYY-MM-DD --trigger-date YYYY-MM-DD
      --assignee-id <uid> --json` — NOTE: --detection-date and --trigger-date are REQUIRED (CLI errors
      without them). Verify: `tornix api risks list <pid> --json`.
  14. **Cost accounts** (per project cost line):
      `tornix data insert project_cost_accounts --data '{"project_id":"<id>","code":"CA-100","name":"...",
      "budgeted_amount":96000,"description":"...","is_active":true,"is_summary":false,"level":1}' --json`
      (table accessible via data API; `api cost accounts` is read-only).
  15. **Contract + payment schedule** (client projects):
      - Partner first (contracts REQUIRE a partner): `tornix data insert partners --data
        '{"name":"<client>","type":"CLIENT","category":"...","status":"ACTIVE",
        "organization_id":"<org>","service":"...","image_url":""}' --json` → full id (NOT truncated!)
      - Contract: `tornix data insert contracts --data '{"project_id":"<id>","name":"...",
        "contract_number":"...","type":"FIXED_PRICE","value":121000,"original_value":121000,
        "currency_code":"SAR","contract_role":"STANDALONE","status":"ACTIVE","partner_id":"<full-id>",
        "start_date":"...","end_date":"...","contract_terms":"..."}' --json`
      - Schedule: `tornix data insert payment_schedules --data '{"contract_id":"<cid>",
        "project_id":"<pid>","organization_id":"<org>","schedule_type":"milestone",
        "total_value":121000,"status":"ACTIVE"}' --json` → schedule id
      - Items: `tornix data insert payment_schedule_items --data '{"schedule_id":"<sid>",
        "contract_id":"<cid>","item_number":1,"description":"...","value":50900,
        "weight_percent":42.07,"planned_date":"...","status":"pending","task_id":"<task>"}' --json`
        (weight_percent = value*100/total; link each item to the milestone task).
  16. **Cleanup baselines**: creating baselines during setup produces junk drafts (cost=0).
      Keep ONLY the final one: delete earlier ones with
      `tornix api gantt delete --data '{"baseline_id":"<id>","project_id":"<pid>"}' --json`.
      Verify final state: `tornix api gantt get <pid> --json` → exactly one ACTIVE primary baseline.
  17. Dashboard picks up the project automatically (health-pulse, home datasets) once
      tasks + budget exist. NOTE: `api gantt schedule`/`schedule-create` (CPM) may 500/timeout
      on the backend — the Gantt still renders from planned dates; don't block on it.
  18. **Full audit checklist** for a Traditional project (run after setup):
      `tornix api gantt get <pid>` (baselines) · `tornix api risks list <pid>` · 
      `tornix data select project_cost_accounts --eq project_id=<pid>` · 
      `tornix data select contracts --eq project_id=<pid>` · 
      `tornix data select payment_schedule_items --eq contract_id=<cid>` ·
      `tornix api documents list --project-id <pid>` · `tornix api projects members <pid>` ·
      `tornix api tasks list <pid>` (dates set) · `tornix data select milestones --eq project_id=<pid>`.
      Invoices/change-orders/payments start empty by design — they fill as the project runs.
- **CLI tool evolves constantly**: new backend scopes get added over time. When a needed
  scope is missing from the CLI, pull it from the backend (`tornix catalog --json` to
  discover, `tornix api <tag> <op>` to call) and update this skill.
- **Agile project setup flow**: create project → add members (`api projects members-create`)
  → set `template_used=AGILE` → insert `projects_agile` row via `data insert` if missing
  (seed fails with 409 "projects_agile row missing") → `api agile seed` (creates columns +
  Release 1.0 + Sprint 1) → rename sprint via `api agile sprints-update` → create tasks
  with `api agile quick-create` (NOTE: quick-create does NOT place tasks in the sprint —
  they land in backlog with `sprint_id=None`; must `api agile move-to-sprint` each) →
  `api agile start` (requires non-empty sprint) → set planned dates via
  `data update project_tasks --data '{"planned_start": ..., "planned_finish": ...}'`.
- **Task statuses**: `NONE` (default) / `IN_PROGRESS` / `IN_RISK` / `COMPLETED` (تامة).
- **Agile flow (new tasks)**: create task → assign to the caller (profile user id) →
  move to the **CURRENT/ACTIVE sprint** (`api agile move-to-sprint`) → set planned
  dates for Timeline (`data update project_tasks --data '{"planned_start": ...,
  "planned_finish": ...}'`) → mark done with `is_done: true` + `percent_complete: 100`
  (status COMPLETED alone does NOT show the task in the Complete column).
  **RULE: new tasks ALWAYS go to the active sprint — NEVER the next/planned sprint.**
  Resolve the active sprint fresh each time via `api agile summary <project>` and use
  its `active_sprint.id` (do not hardcode — it changes when sprints roll).
  **RULE: marking a task done = move it to the Done column** (`api agile move
  --to-column-id <done-column-id>`) + `is_done: true` + `percent_complete: 100` +
  status COMPLETED. Setting is_done alone leaves the card stranded in its old column
  (e.g. Proposed) — the board shows the column, not the flag. Resolve the done column
  id fresh via `api agile board` (do not hardcode).
- **Active sprint**: resolve fresh via `api agile summary` — do not hardcode
  (sprints roll weekly; the id changes).
- **Task detail ops**: `api agile blocked` (blockers), `api tasks dependencies` /
  `dependencies-create` (deps), `api tasks progress` / `progress-create` (progress),
  `api tasks requirements` (DoR evidence), `api agile points` / `estimate-hours` /
  `work-item-type` / `epic` / `assignees` / `accept` / `dod` / `dor` (task-level agile).
- **New agile reports**: `api agile performance` / `trends` / `scope` / `hours` /
  `baseline` / `flow-breakdown` / `schedule` / `changes-since-refinement` / `insights` /
  `work-grouping` / `estimation-rounds` (poker) / `refinement` / `similar` / `suggest-draft`.
- **Timeline/Gantt**: tasks appear when `planned_start`/`planned_finish` are set
  (via `data update project_tasks`). `api gantt wbs-get` / `schedule` / `variance` /
  `baselines` for schedule work.
- **WBS tree**: the Gantt renders a real WBS hierarchy when `gantt_wbs` rows exist
  and tasks carry `wbs_id` (frontend `gantt-adapter.service.ts` `transformWithWbsTree`).
  Sections are ignored when a WBS tree exists. `ganttWbs` IS in
  `PROJECT_SCOPED_DELEGATES` (direct) → INSERT allowed via data proxy:
  `tornix data insert gantt_wbs --data '{"project_id":"<id>","name":"...","code":"...",
  "level":0,"sort_order":0,"path":"..."}' --json`, then link tasks:
  `tornix data update project_tasks --eq id=<task> --data '{"wbs_id":"<node>"}' --json`.
  Empty branches are dropped from the Gantt — only nodes with tasks beneath them render.
- **File upload to File Center**: `tornix file upload <path> --project <id> [--task <id>]`
  uploads a local file to S3 (presigned URL) and syncs it into the project's File
  Center in one step. `--task` attaches it to a task (stored in document metadata
  `task_id` — how the frontend renders task attachments). Verify with
  `tornix data select documents --filter "metadata->>task_id=eq.<task_id>"`.
  PITFALL: `data select/update/delete` on `documents` needs `--filter "col=eq.val"`
  (raw PostgREST form) — the `--eq col=val` shorthand double-prefixes to `eq.eq.val`
  and silently returns `[]` on this table.
- **Reading/downloading documents**: `tornix api documents list --project-id <id> --json`
  (names + sizes + `document_path`), `tornix api documents get <doc-id> --json` (details).
  To fetch the actual file content: `tornix api storage signed-url --bucket files
  --path "<document_path>" --download true --json` → signed S3 URL (1h), then curl it.
  The `document_path` is already `files/<project_id>/<uuid>.<ext>` — pass it verbatim.

## Full command list (modular)
The command reference is split per backend scope so you load ONLY what the task needs:
- **Index**: `references/commands.md` — table of every scope → file (load this first to pick the right file).
- **Core**: `references/scopes/core.md` — top-level commands (auth, config, data proxy, projects, tasks, file, meetings, deep-research, rpc, catalog, skill).
- **Per scope**: `references/scopes/<tag>.md` — one file per `tornix api <tag>` (e.g. `agile.md`, `gantt.md`, `documents.md`, `strategy.md`, `meetings.md`, `storage.md`).
Load via `skill_view(name='tornix', file_path='references/scopes/<tag>.md')`. Regenerate anytime with `tornix skill generate --out <path>` (then re-apply the Authentication section above and re-run the split script).
