# `tornix api twin` — 6 commands

- `tornix api twin contact-point --json` — TwinPerformanceController_getContactPoint
- `tornix api twin decide --json` — Record a human decision on a twin card: closes it, stamps the decision and WHO made it (from the token, not the body).
- `tornix api twin fires --json` — Recent fires of one hook card (newest first): the event, the source row that triggered it, and the child card it spawned. Org-scoped to the caller.
- `tornix api twin home --json` — Every dataset the Twin page needs, in one request. Pass ?datasets= to fetch only what the open tab renders. The twin itself is always returned.
- `tornix api twin performance-contact-point-replace --json` — Name the single human the outside world talks to about the automated work (item 24, criterion 2). Organization admins only.
- `tornix api twin report --json` — Monthly performance report for the org’s twin cards: how many closed with no human in the loop, how many a person confirmed, how many escalated, plus per-kind and per-hook-event breakdowns.

(6 commands)
