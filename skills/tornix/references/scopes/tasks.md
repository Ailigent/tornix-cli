# `tornix api tasks` — 16 commands

- `tornix api tasks comments --json` — Get task comments
- `tornix api tasks comments-create --json` — Add comment to task
- `tornix api tasks delete --json` — Delete task
- `tornix api tasks dependencies --json` — Get task dependencies
- `tornix api tasks dependencies-create --json` — Add task dependency
- `tornix api tasks extract --json` — Extract task drafts from a chat message or long text via AI
- `tornix api tasks extract-video --json` — Extract task drafts from a chat video/audio attachment. Reuses a stored transcript, transcribes audio inline, or kicks off the video summary worker and returns status:'transcribing' for the caller to poll.
- `tornix api tasks extract-voice --json` — Extract task drafts from a voice recording (audio passed as base64) via Gemini multimodal
- `tornix api tasks from-drafts --json` — Bulk create tasks from AI-generated drafts (chat message or voice extraction)
- `tornix api tasks get --json` — Get task by ID
- `tornix api tasks list --json` — List tasks for a project
- `tornix api tasks progress --json` — Progress ledger for a task, newest first
- `tornix api tasks progress-create --json` — Record a progress step, with the evidence behind it
- `tornix api tasks replace --json` — Update task
- `tornix api tasks requirements --json` — Whether recording progress on this task requires evidence
- `tornix api tasks tag-suggestions --json` — List distinct task tags in the current organization

(16 commands)
