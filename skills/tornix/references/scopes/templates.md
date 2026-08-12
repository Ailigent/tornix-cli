# `tornix api templates` — 15 commands

- `tornix api templates create --json` — Create a request template from an uploaded file
- `tornix api templates delete --json` — Delete a request template + its source file
- `tornix api templates dismiss --json` — Hide an extraction job from the list (published or dismissed)
- `tornix api templates duplicate --json` — Clone a template (copies its source file + approval path)
- `tornix api templates extract-jobs --json` — List recent extraction jobs (live rows in the Templates list)
- `tornix api templates extract-jobs-create --json` — Create a background batch extraction job for uploaded sources
- `tornix api templates fill --json` — Render a filled document from a values map
- `tornix api templates fill-async --json` — Queue a background fill so the requester submit returns instantly
- `tornix api templates get --json` — Poll a background extraction job (progress + results)
- `tornix api templates list --json` — List request templates
- `tornix api templates reextract --json` — Re-run AI schema extraction on the stored source
- `tornix api templates reorder --json` — Set the order the org's templates are listed in. The array is the whole list, in its new order.
- `tornix api templates replace --json` — Update a request template (labels / status / form schema)
- `tornix api templates retry-fill-create --json` — Re-run a failed background fill for a request (recover from a failed generation)
- `tornix api templates templates-get --json` — Get a request template (with signed source URL)

(15 commands)
