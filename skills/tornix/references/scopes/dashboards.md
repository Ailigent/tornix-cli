# `tornix api dashboards` — 16 commands

- `tornix api dashboards create --json` — Create a dashboard
- `tornix api dashboards delete --json` — Delete a dashboard
- `tornix api dashboards get --json` — Get a single dashboard
- `tornix api dashboards health-pulse --json` — The C-Level health pulse (15 KPIs), aggregated in SQL. Replaces a client-side reduction over every project_tasks row in the org.
- `tornix api dashboards home --json` — Every dataset the dashboard home page needs, in one request. Pass ?datasets= to fetch only what the mounted widgets consume.
- `tornix api dashboards list --json` — List the current user dashboards
- `tornix api dashboards migrate-legacy --json` — One-time seed from legacy localStorage
- `tornix api dashboards office-performance --json` — Office Performance: governance cadence (90d), compliance watchlist, services delivered (30d)
- `tornix api dashboards overview --json` — Aggregated PMO command-center KPIs (11 cards) for a portfolio or the entire org
- `tornix api dashboards portfolio-scorecards --json` — Per-portfolio scorecards: canonical confidence score, quarterly trend, 4 metric bars
- `tornix api dashboards portfolios --json` — Portfolios dashboard: KPI strip, alignment-vs-value bubbles, investment donut, rebalancing recs
- `tornix api dashboards programs --json` — Programs dashboard: 4 top-strip stats and per-program rows (health/SPI/CPI/benefits/dependencies)
- `tornix api dashboards project-metrics-history --json` — Monthly avg SPI/CPI/earned-value series for the org, plus vs-3-months-ago deltas
- `tornix api dashboards project-metrics-history-snapshot-create --json` — Force the monthly project-metrics snapshot (cron runs 04:00 daily)
- `tornix api dashboards snapshot --json` — Force a snapshot of the open quarter for every portfolio (the daily cron does this at 03:00)
- `tornix api dashboards update --json` — Update a dashboard

(16 commands)
