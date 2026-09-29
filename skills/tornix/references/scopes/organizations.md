# `tornix api organizations` — 13 commands

- `tornix api organizations create --json` — Create organization
- `tornix api organizations delete --json` — Delete organization (only the creator can delete)
- `tornix api organizations get --json` — Get organization by ID
- `tornix api organizations list --json` — List user organizations
- `tornix api organizations logo --json` — Get the organization logo (null when unset)
- `tornix api organizations logo-delete --json` — Remove the organization logo (org admin only)
- `tornix api organizations logo-replace --json` — Replace the organization logo (org admin only)
- `tornix api organizations member-type --json` — Flip a member between internal (client staff) and provider (Ailigent)
- `tornix api organizations members --json` — List organization members
- `tornix api organizations members-create --json` — Add member to organization
- `tornix api organizations provider-members --json` — List the org members flagged as provider (Ailigent) staff
- `tornix api organizations roles --json` — List organization roles
- `tornix api organizations team-workload --json` — Per-member workload (remaining hours vs capacity) in one query

(13 commands)
