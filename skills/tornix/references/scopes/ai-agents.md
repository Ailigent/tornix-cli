# `tornix api ai-agents` — 15 commands

- `tornix api ai-agents cancel --json` — Cancel a running agent execution
- `tornix api ai-agents create --json` — Create AI agent
- `tornix api ai-agents delete --json` — Delete AI agent
- `tornix api ai-agents get --json` — Get AI agent by ID
- `tornix api ai-agents list --json` — List AI agents, newest first, each with its latest run (minus the run's output/error bodies). Filters on the run-derived effective status, so the status chips paginate server-side.
- `tornix api ai-agents pdf --json` — Download a run report as a PDF
- `tornix api ai-agents recent-chats --json` — Find recent chat IDs from the shared Telegram bot (used by the create-agent UI to auto-fill the telegram_chat_id field)
- `tornix api ai-agents replace --json` — Update AI agent
- `tornix api ai-agents run --json` — Manually trigger agent execution
- `tornix api ai-agents runs --json` — Get agent run history
- `tornix api ai-agents seed-defaults --json` — Seed default AI agents for the organization
- `tornix api ai-agents start --json` — Start a one-click Telegram linking flow: generates a unique token and returns the t.me deep link. Frontend opens the link and polls /telegram/link/status until the user presses Start in Telegram.
- `tornix api ai-agents status --json` — Poll endpoint for the one-click Telegram linking flow. Returns { linked, chat_id?, chat_title? } when the user has pressed Start in Telegram, or { linked: false, expired? } while waiting.
- `tornix api ai-agents stream --json` — Trigger agent and stream live events back as SSE
- `tornix api ai-agents ui --json` — Get a run as OpenUI Lang (rich UI) when available

(15 commands)
