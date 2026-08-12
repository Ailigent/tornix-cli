# `tornix api cost-categories` — 4 commands

- `tornix api cost-categories create --json` — Create a cost category
- `tornix api cost-categories delete --json` — Soft-delete a cost category (sets is_active=false; never hard-deletes — Odoo depends on slug stability)
- `tornix api cost-categories list --json` — List cost categories (defaults to active)
- `tornix api cost-categories update --json` — Update a cost category (slug is read-only)

(4 commands)
