# `tornix api memory` — 9 commands

- `tornix api memory create --json` — memory(action, target, content) — add/replace/remove a fact or the profile
- `tornix api memory delete --json` — Delete one memory entry by id (own personal entry or any org-wide entry)
- `tornix api memory extract --json` — Proactive extraction / correction capture (called by the orchestrator)
- `tornix api memory list --json` — List all memory entries for a scope (namespace user|org) — the Memory tab
- `tornix api memory recall --json` — The policy-only recall block to inject into the system prompt
- `tornix api memory scope --json` — Move a memory entry between personal and organization scope
- `tornix api memory search --json` — memory_search(query, category) — full-text search over memory
- `tornix api memory sessions-search --json` — session_search(query) — full-text search over past conversations
- `tornix api memory skills --json` — skill_manage(action, scope, …) — CRUD reusable procedure skills

(9 commands)
