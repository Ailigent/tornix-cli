# `tornix api company-admin-talon` — 6 commands

- `tornix api company-admin-talon adjust --json` — [Super admin] Correct one Talon user's balance in either direction — a NEGATIVE amount is the only way to take credit back
- `tornix api company-admin-talon status --json` — [Super admin] Is this deployment configured to talk to a sibling Talon box, and is it reachable
- `tornix api company-admin-talon topup --json` — [Super admin] Add credit to one Talon user's wallet — forwarded to Talon's `/credits/admin/accounts/:id/topup`, which writes its own ledger line
- `tornix api company-admin-talon tornix-link --json` — [Super admin] Identity link ONLY — records that this Talon user IS the given Tornix member. Never provisions a hermes-sandbox gateway.
- `tornix api company-admin-talon users --json` — [Super admin] Every Talon user on this deployment's sibling box, with its resolved Tornix link (id-resolved locally) — NOT credit balance, see talon.service.ts
- `tornix api company-admin-talon users-tornix-link-delete --json` — [Super admin] Remove the identity link — never touches the Tornix account itself

(6 commands)
