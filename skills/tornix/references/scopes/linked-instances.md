# `tornix api linked-instances` — 14 commands

- `tornix api linked-instances assertion --json` — Mint a one-time signed hop into a linked deployment
- `tornix api linked-instances create --json` — [super-admin] Register a linked instance
- `tornix api linked-instances delete --json` — [super-admin] Revoke a trusted peer (or an unredeemed pairing code)
- `tornix api linked-instances import --json` — Add a server from another deployment's pairing code
- `tornix api linked-instances linked-instances-delete --json` — Remove a linked server you own (a super-admin may remove any)
- `tornix api linked-instances linked-instances-update --json` — Update a linked server you own (a super-admin may update any)
- `tornix api linked-instances list --json` — Linked servers this account owns (a super-admin sees every one)
- `tornix api linked-instances pairing-code --json` — [super-admin] Mint a one-time pairing code for this deployment
- `tornix api linked-instances peers --json` — [super-admin] Deployments allowed to sign into this one (no secrets)
- `tornix api linked-instances self --json` — This deployment's own federation identity and switch
- `tornix api linked-instances self-replace --json` — [super-admin] Set this deployment's display name / on-off switch
- `tornix api linked-instances test --json` — Probe a linked server you own (a super-admin may probe any)
- `tornix api linked-instances update --json` — [super-admin] Enable/disable or relabel a trusted peer
- `tornix api linked-instances workspaces --json` — Same-server organizations plus any visible linked deployments

(14 commands)
