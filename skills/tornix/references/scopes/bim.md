# `tornix api bim` — 33 commands

- `tornix api bim 5d-elements --json` — Per-element cost and CPI band (for the 3D viewer)
- `tornix api bim 5d-progress-rules-replace --json` — Save the organization's weighted progress-measurement stages (manage_bim)
- `tornix api bim 5d-summary --json` — Model BAC/PV/EV/AC/committed/EAC, CPI/SPI, coverage and cost breakdowns on a date
- `tornix api bim acknowledge --json` — Clear the scope-change flags a reviewer has looked at
- `tornix api bim bulk --json` — BimRegisterController_bulk
- `tornix api bim cde-history --json` — BimRegisterController_history
- `tornix api bim cde-transition --json` — BimRegisterController_transition
- `tornix api bim cost --json` — One element: quantity → BOQ → cost code → budget → committed → actual → forecast
- `tornix api bim delete --json` — BimRegisterController_deleteZone
- `tornix api bim element-ids --json` — Model + GlobalId of every element matching the register filters (for Show in 3D)
- `tornix api bim elements --json` — Per-element planned/actual state and status on a date (for the 3D viewer)
- `tornix api bim elements-issues-delete --json` — BimRegisterController_unlinkIssue
- `tornix api bim get --json` — BimRegisterController_elementCard
- `tornix api bim issues --json` — BimRegisterController_linkIssue
- `tornix api bim locations --json` — BimRegisterController_locations
- `tornix api bim locations-create --json` — BimRegisterController_createZone
- `tornix api bim lookahead --json` — Activities with model elements planned in the next weeks
- `tornix api bim models --json` — Latest model versions visible to the caller (WIP: uploader and BIM managers only)
- `tornix api bim my-permissions --json` — Resolve the caller's effective BIM permissions for a project
- `tornix api bim new --json` — BimRegisterController_createIssue
- `tornix api bim options --json` — Zones, WBS nodes, BOQ items and members to pick from when editing elements
- `tornix api bim progress-rules --json` — Bim5dController_rules
- `tornix api bim quantities --json` — Model quantity takeoff and BOQ quantity check
- `tornix api bim register-elements --json` — BimRegisterController_elements
- `tornix api bim register-elements-update --json` — BimRegisterController_patchElement
- `tornix api bim register-summary --json` — BimRegisterController_summary
- `tornix api bim scope-changes --json` — A project's activities whose modelled scope changed
- `tornix api bim scope-changes-create --json` — Reflect a committed BIM edit onto the activities that claim those elements
- `tornix api bim sequence --json` — Construction sequence: activities with elements, in planned order
- `tornix api bim sequence-elements --json` — Bim4dController_sequenceElements
- `tornix api bim summary --json` — Element schedule status, planned vs actual %, and deviations on a date
- `tornix api bim sync --json` — Read a model into the BIM element register (keeps user-entered data)
- `tornix api bim update --json` — BimRegisterController_updateLocation

(33 commands)
