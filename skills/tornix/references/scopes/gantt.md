# `tornix api gantt` — 34 commands

- `tornix api gantt activate --json` — Activate an approved baseline (snapshot + lock)
- `tornix api gantt baselines --json` — Create a baseline (project_id in body)
- `tornix api gantt calendars-get --json` — Get project calendars
- `tornix api gantt create --json` — Create a baseline
- `tornix api gantt delete --json` — Delete a baseline
- `tornix api gantt exceptions --json` — Replace calendar exceptions atomically using the loaded calendar version
- `tornix api gantt export-xer-create --json` — Export to P6 XER format (base64 JSON)
- `tornix api gantt get --json` — List project baselines
- `tornix api gantt import --json` — Import structural WBS nodes with parent/order links
- `tornix api gantt import-xer-create --json` — Import P6 XER file (project_id in body)
- `tornix api gantt milestones --json` — List milestones for a WBS node
- `tornix api gantt move --json` — Move a WBS node in its project hierarchy
- `tornix api gantt nodes --json` — Create a structural WBS node
- `tornix api gantt nodes-milestones-create --json` — Create a weighted WBS milestone
- `tornix api gantt nodes-milestones-delete --json` — Delete a weighted WBS milestone
- `tornix api gantt nodes-milestones-update --json` — Update a weighted WBS milestone
- `tornix api gantt reject --json` — Reject a baseline request
- `tornix api gantt request --json` — Create a DRAFT baseline request (approval flow)
- `tornix api gantt resource-leveling-create --json` — Run resource leveling to resolve over-allocation
- `tornix api gantt resources-get --json` — Get project resources
- `tornix api gantt restore-baseline --json` — Restore schedule from baseline (project_id in body)
- `tornix api gantt restore-baseline-create --json` — Restore schedule from a baseline (dates_only or full mode)
- `tornix api gantt schedule --json` — Run CPM scheduling (project_id in body)
- `tornix api gantt schedule-create --json` — Run CPM scheduling (forward/backward pass)
- `tornix api gantt set-locked --json` — Lock (freeze) or unlock a baseline as a fixed comparison snapshot
- `tornix api gantt set-primary --json` — Set a baseline as primary (atomic)
- `tornix api gantt update --json` — Update WBS administrative fields
- `tornix api gantt update-status --json` — Update baseline status
- `tornix api gantt variance --json` — Calculate baseline variance (project_id in body)
- `tornix api gantt variance-create --json` — Calculate baseline variance (schedule & cost)
- `tornix api gantt wbs-get --json` — Get WBS structure
- `tornix api gantt wbs-nodes-delete --json` — Delete a structural WBS node
- `tornix api gantt xer --json` — Export to P6 XER format (project_id in body)
- `tornix api gantt xer-create --json` — Import P6 XER file

(34 commands)
