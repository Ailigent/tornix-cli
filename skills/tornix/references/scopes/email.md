# `tornix api email` — 32 commands

- `tornix api email accounts --json` — EmailController_getAccounts
- `tornix api email accounts-create --json` — EmailController_addAccount
- `tornix api email actions --json` — Perform email actions: delete, star, markRead (used by AI agent)
- `tornix api email attachment --json` — Fetch a single IMAP attachment by UID and index
- `tornix api email classify-batch --json` — Enqueue background AI classification for a batch of emails. Returns immediately; classification + project suggestions are persisted asynchronously.
- `tornix api email connect --json` — Exchange Google OAuth code for tokens and create/update email account
- `tornix api email delete --json` — EmailController_removeAccount
- `tornix api email digest-fetch-create --json` — Fetch emails for AI digest (used by Super Agent)
- `tornix api email fetch --json` — Fetch emails via IMAP (used by AI agent)
- `tornix api email folders --json` — System folders (Inbox, Starred, Sent, Drafts, Archive, Spam, Trash) with total + unread counts, and the mailbox path each resolved to on this account. NOT the same as /labels, which returns the user’s own tags.
- `tornix api email history --json` — Relationship history with a sender in the caller's OWN mailbox: prior messages in the sender's conversations, plus their linked projects and any tasks they spawned. Optionally filtered to a project.
- `tornix api email identity --json` — Resolve a sender email address to the person/entity it belongs to (teammate, partner contact, vendor, …) and the project(s) they relate to. Project links are filtered to the caller's accessible projects.
- `tornix api email imap-actions-create --json` — Perform IMAP flag/move actions (star, read, delete, archive)
- `tornix api email imap-connect-create --json` — Test IMAP+SMTP connection and save credentials
- `tornix api email imap-fetch-create --json` — Fetch emails via IMAP
- `tornix api email labels --json` — EmailController_getLabels
- `tornix api email messages --json` — EmailController_getMessages
- `tornix api email previews --json` — Signed preview URLs for a message’s IMAGE attachments, served from the archive in object storage. Only images, only files the archiver has already stored — anything else is simply absent and the client keeps its file glyph.
- `tornix api email refresh-token --json` — Refresh Gmail access token using stored refresh token
- `tornix api email reminders --json` — List pending reminders, optionally for one message.
- `tornix api email reminders-create --json` — Remind me about this email at a time. Server-side, so it survives a reinstall and reaches whichever device the reader is holding.
- `tornix api email reminders-delete --json` — Cancel a pending reminder.
- `tornix api email schedule --json` — Queue an email to go out later. The row is durable and re-armed on boot, so a queue flush cannot lose it.
- `tornix api email scheduled --json` — List the caller’s pending scheduled emails.
- `tornix api email scheduled-delete --json` — Cancel a pending scheduled email.
- `tornix api email seen --json` — Mark the mailbox as looked at. Moves the window the briefing counts from. Called when the inbox is OPENED — never on sync, which would zero the briefing for a reader who saw nothing.
- `tornix api email send --json` — Send email via SMTP (used by AI agent)
- `tornix api email send-create --json` — Send a transactional email via Brevo SMTP API
- `tornix api email smtp-send-create --json` — Send email via SMTP using stored account credentials
- `tornix api email sync --json` — EmailController_syncAccount
- `tornix api email sync-now --json` — Pull new Gmail messages for the current user since last_sync_at and enqueue classification. Awaits the Gmail fetch + enqueue (typically <5s) but the LLM work itself runs async in BullMQ.
- `tornix api email triage-summary --json` — Inbox briefing: how many emails are in each triage bucket since the reader last looked, plus the ones needing a decision. Counts come from the classifier, over the WHOLE synced mailbox — not the page the client has loaded.

(32 commands)
