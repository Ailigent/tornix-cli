# `tornix api pre-project` — 6 commands

- `tornix api pre-project create --json` — Create a pre-project initiative (requester = caller)
- `tornix api pre-project create-project --json` — Create the project from an approved charter (guards CHARTER_APPROVED)
- `tornix api pre-project documents --json` — Link the business case and/or charter document to this initiative
- `tornix api pre-project get --json` — Get an initiative by id
- `tornix api pre-project list --json` — List initiatives in the organization, newest first
- `tornix api pre-project submit --json` — Submit the business case or charter for approval (creates/resends the ApprovalRequest server-side)

(6 commands)
