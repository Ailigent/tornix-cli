# `tornix api ui-permissions` — 2 commands

- `tornix api ui-permissions me --json` — Caller's effective UI-permission map for one organization, optionally scoped to one project — the tab/button visibility layer this feeds (see ui-permissions.registry.ts)
- `tornix api ui-permissions registry --json` — The UI-permission registry — sections, keys and defaults. The frontend mirror (frontend/src/shared/permissions) asserts its own key set against this same list.

(2 commands)
