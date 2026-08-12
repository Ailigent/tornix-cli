# `tornix api invitations` — 4 commands

- `tornix api invitations accept --json` — Accept a pending invitation for the calling user — sets the caller's own profile role from the server-side invitation record (P5 C2: the only non-proxy path allowed to write profiles.role for a self-accept)
- `tornix api invitations invite-to-org --json` — Add an existing user to an organization and notify them
- `tornix api invitations notify-existing --json` — Notify an existing user that they were added to an organization
- `tornix api invitations send --json` — Invite a new user by email (creates account + sends invitation)

(4 commands)
