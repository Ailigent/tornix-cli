# `tornix api request-board` — 19 commands

- `tornix api request-board assignee --json` — Hand a card to someone without moving it between columns
- `tornix api request-board bulk --json` — Import many cards at once into the intake column. Bad rows are skipped and reported per row rather than failing the whole file.
- `tornix api request-board columns --json` — List the org's board columns (seeds defaults on first open)
- `tornix api request-board columns-create --json` — Append a column
- `tornix api request-board delete --json` — Delete an empty column (refuses while it still holds cards)
- `tornix api request-board events --json` — One card's full history, newest first
- `tornix api request-board get --json` — Tickets extracted from a chat message + the board columns, for the "tickets from this message" status modal
- `tornix api request-board items --json` — Raise a card (lands in the intake column, held by its creator)
- `tornix api request-board items-delete --json` — Archive a card (leaves the board, keeps its history)
- `tornix api request-board items-tags-delete --json` — Remove a label from a card (holder only)
- `tornix api request-board items-update --json` — Edit a card's content
- `tornix api request-board list --json` — The whole board in one call: columns + cards + people. Filters are CSV and AND together; `assignee_id=unassigned` matches cards nobody holds.
- `tornix api request-board move --json` — Move a card to a column and hand it to the next person in one action
- `tornix api request-board reorder --json` — Reorder columns by id array
- `tornix api request-board routing --json` — Set what happens to a card that lands in a stage: keep it with its holder, ask the mover who takes it, route it to a job title (optionally per discipline), or send it back to the requester. Replaces the whole configuration.
- `tornix api request-board source-message --json` — A ticket's source chat message as a { room_id, message_id } deep-link target
- `tornix api request-board tag-suggestions --json` — Labels the organization already uses, most-used first
- `tornix api request-board tags --json` — Label a card (holder only). Re-adding an existing label is a no-op.
- `tornix api request-board update --json` — Relabel / recolor / re-kind a column

(19 commands)
