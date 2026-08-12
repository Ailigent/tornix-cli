---
user: <email>
user_id: <uuid>
org: <org-name> (<org-id>)
default_project: <name> (<project-id>)
language: <e.g. Arabic (Egyptian) + English>
---

# Profile: <Name> (<email>)

## Identity
- user id: `<uuid>`
- org: `<org-name>` `<org-id>`
- default project: `<name>` `<project-id>`

## Team (org members)
| Member | Role | user id |
|---|---|---|
| <name> | <role> | <uuid> |

## Conventions
- <language / communication style>
- <default project when none named>
- <any user-specific rules>

---
## How to fill this profile (bootstrap)
Run these and paste the results:
1. `tornix auth whoami --json` → id + email
2. `tornix api organizations list --json` → orgs
3. `tornix projects list --json` → projects (pick the default)
4. For team IDs: `tornix api projects members <project-id> --json` → user_ids
   (then resolve names via `tornix api users list --json` or chat participants)
