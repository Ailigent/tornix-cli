# `tornix api dashboards` — 12 commands

- `tornix api dashboards create --json` — Create a dashboard
- `tornix api dashboards delete --json` — Delete a dashboard
- `tornix api dashboards get --json` — Get a single dashboard
- `tornix api dashboards health-pulse --json` — The C-Level health pulse (15 KPIs), aggregated in SQL. Replaces a client-side reduction over every project_tasks row in the org.
- `tornix api dashboards home --json` — Every dataset the dashboard home page needs, in one request. Pass ?datasets= to fetch only what the mounted widgets consume.
- `tornix api dashboards list --json` — List the current user dashboards
- `tornix api dashboards migrate-legacy --json` — One-time seed from legacy localStorage
- `tornix api dashboards office-performance --json` — Office Performance: governance cadence (90d), compliance watchlist, services delivered (30d)
- `tornix api dashboards overview --json` — Aggregated PMO command-center KPIs (11 cards) for a portfolio or the entire org
- `tornix api dashboards portfolios --json` — Portfolios dashboard: KPI strip, alignment-vs-value bubbles, investment donut, rebalancing recs
- `tornix api dashboards programs --json` — Programs dashboard: 4 top-strip stats and per-program rows (health/SPI/CPI/benefits/dependencies)
- `tornix api dashboards update --json` — Update a dashboard

(12 commands)
