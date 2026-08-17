# `tornix api strategy-draft` — 17 commands

- `tornix api strategy-draft activate --json` — Activate a draft: materialize it as a live, versioned strategy (archives the predecessor)
- `tornix api strategy-draft activation-status --json` — Where the activation job has got to (survives a closed tab)
- `tornix api strategy-draft create --json` — Open a draft that revises a live strategy (activation stamps v1.1, v1.2 …)
- `tornix api strategy-draft delete --json` — Delete a draft (refused once it has been activated)
- `tornix api strategy-draft drafts --json` — List strategy drafts for the organization
- `tornix api strategy-draft drafts-items-delete --json` — Discard a draft item (kept, not deleted)
- `tornix api strategy-draft drafts-items-update --json` — Edit a draft item. The payload is MERGED, not replaced. Marks the item as edited by the user unless `as_proposal: true` — which is how an agent suggests a value (e.g. a project link) without claiming the card as a human decision.
- `tornix api strategy-draft drafts-sources-delete --json` — Remove a source (the items it produced survive)
- `tornix api strategy-draft extract --json` — Read every queued source and stream the items as they land (SSE)
- `tornix api strategy-draft get --json` — Get a draft with its sources, items, flags, counters and warnings
- `tornix api strategy-draft items --json` — Add an item by hand (theme / objective / kpi / initiative)
- `tornix api strategy-draft phase --json` — Report where a long build has got to (phase, one-line detail, steps done/total)
- `tornix api strategy-draft resolve --json` — Resolve a conflict or duplicate flag
- `tornix api strategy-draft retry --json` — Re-read a source that failed or produced nothing
- `tornix api strategy-draft sources --json` — Add a source: an uploaded file or a block of pasted text
- `tornix api strategy-draft strategy-drafts-create --json` — Start a new strategy draft (AI or manual)
- `tornix api strategy-draft update --json` — Rename a draft / edit its brief

(17 commands)
