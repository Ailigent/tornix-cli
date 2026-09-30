# `tornix api organizations` — 16 commands

- `tornix api organizations assignment --json` — Set a member's final project set in this organization, and optionally their job title and company label, in one transaction
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
- `tornix api organizations members-delete --json` — Remove a member from the organization (membership + every project membership in it, atomically). Organization admin, or yourself; never the last full-access member.
- `tornix api organizations project-workloads --json` — Project-specific workload (this project's tasks only) for every project in one query
- `tornix api organizations provider-members --json` — List the org members flagged as provider (Ailigent) staff
- `tornix api organizations roles --json` — List organization roles
- `tornix api organizations team-workload --json` — Per-member load: real estimated hours of the member's open assigned tasks ÷ their weekly capacity. With project_id it counts only that project (member on THIS project — the same numerator and capacity a project card sums); without it, all the org's projects (member across the org, on a standard week); project_ids narrows the org-wide view to a set of projects. Never guesses hours: null hours/percentage = active work but none estimated.

(16 commands)
