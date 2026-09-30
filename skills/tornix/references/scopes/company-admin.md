# `tornix api company-admin` — 24 commands

- `tornix api company-admin access-status --json` — [Org admin] Set a member's access lifecycle status (pending/approved/rejected) — org-scoped equivalent of /users/admin/set-access-status. Refuses the caller's own account and an identity-locked account.
- `tornix api company-admin activity --json` — [Org admin] Who did what to whom on this screen — members added / imported / deleted, role and access-status changes, plus every administrative credit adjustment with its reason
- `tornix api company-admin bulk-projects --json` — [Org admin] Apply a project set to many members at once, within one organization ('add' = union, 'set' = replace). Capped at 200 members per call.
- `tornix api company-admin company-admin-projects --json` — [Org admin] Projects linked to ONE organization, with their members
- `tornix api company-admin credit --json` — [Super admin] Adjust a member's credit balance within one organization — delegates to CreditsService.adminAdjustCredits so the ledger stays in one place.
- `tornix api company-admin get --json` — [Org admin] Everything the member detail drawer shows, in one call
- `tornix api company-admin job-titles --json` — [Org admin] One organization's job titles (organization_roles) with member counts, ordered by member count desc — the real per-project permission layer, distinct from the two-value global role
- `tornix api company-admin job-titles-create --json` — [Org admin] Create a new job title by cloning an existing one's permissions — the safer path for "change it for just this one member", optionally assigning the new title to one member in the same call
- `tornix api company-admin job-titles-permissions-update --json` — [Org admin] Update a job title's permissions — writes the SHARED role, affecting every member who currently holds it, not only the member the caller has open
- `tornix api company-admin mail-accounts --json` — [Org admin] The mailboxes members of one organization have connected
- `tornix api company-admin mail-settings --json` — [Org admin] The company mail settings for one organization
- `tornix api company-admin mail-settings-replace --json` — [Org admin] Create or update one company mail setting
- `tornix api company-admin members --json` — [Org admin] Members of ONE organization — search/filter/sort/paginate on the server
- `tornix api company-admin members-delete --json` — [Org admin] Delete a member's ACCOUNT (not just its membership). Refuses the caller's own account, an identity-locked account, an account holding super-admin access, and an account referenced by partner reviews / supplier evaluations (reason `referenced_by_business_records` — reject its access instead).
- `tornix api company-admin organization-settings --json` — [Org admin] AI access / transcription engine / perspectives toggles for one organization
- `tornix api company-admin organization-settings-update --json` — [Org admin] Update only the settings keys provided
- `tornix api company-admin organizations --json` — Organizations the caller administers (member + owner/C_LEVEL). A platform super admin gets the ones they belong to, or every organization with ?all=true
- `tornix api company-admin permissions --json` — [Org admin] One job title's full permission set (~73 booleans)
- `tornix api company-admin projects --json` — [Org admin] Set the FINAL SET of projects a member belongs to within one organization — the server diffs against current memberships and adds/removes only the delta. Never touches this member's memberships in other organizations.
- `tornix api company-admin role --json` — [Org admin] Set a member's global role (C_LEVEL / REGULAR_MANAGER / null) — org-scoped equivalent of /users/admin/set-role. Refuses the caller's own account and an identity-locked account.
- `tornix api company-admin ticket-approval-flow --json` — [Org admin] Choose (or clear) the approval flow a support ticket walks
- `tornix api company-admin ticket-approval-flows --json` — [Org admin] Approval flows a support ticket can walk before it is sent
- `tornix api company-admin unlock-login --json` — [Org admin] Lift a member's login lockout (too many failed password / 2FA attempts) before its 5 minutes run out. Changes no credential, so it is not identity-locked.
- `tornix api company-admin update --json` — [Org admin] Update full_name/phone/job_title/email — role, access_status, password and super-admin status go through /users/admin/*, not here

(24 commands)
