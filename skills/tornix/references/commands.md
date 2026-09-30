<!-- split-skill-scopes-index -->

# Tornix command reference — modular index

Commands are split per backend scope. Load ONLY the file matching your task (via skill_view file_path) — do not load the whole tree.

## Core (top-level)
- `references/scopes/core.md` — config, data proxy, projects, tasks, file, meetings, deep-research, rpc, catalog, skill

## API scopes (one file per tag)
| Scope | File | # | Use when |
|---|---|---:|---|
| access-requests | `references/scopes/access-requests.md` | 5 | Approve an access request (super-admin) |
| agile | `references/scopes/agile.md` | 131 | Accept a proposed item for the team |
| ai-agents | `references/scopes/ai-agents.md` | 15 | Cancel a running agent execution |
| ai-chat | `references/scopes/ai-chat.md` | 16 | AiChatController_setRoomArchived |
| ai-context | `references/scopes/ai-context.md` | 1 | Shared AI context for the caller organization |
| ai-proxy | `references/scopes/ai-proxy.md` | 80 | AiProxyController_proxyReports_get |
| ai-widgets | `references/scopes/ai-widgets.md` | 6 | Save a generated widget config to the library |
| app-versions | `references/scopes/app-versions.md` | 13 | Re-run AI feature extraction on the release video |
| approvals | `references/scopes/approvals.md` | 60 | Get cached AI review result for a request |
| benefits | `references/scopes/benefits.md` | 7 | Create a benefit |
| bim | `references/scopes/bim.md` | 33 | Per-element cost and CPI band (for the 3D viewer) |
| calendar | `references/scopes/calendar.md` | 3 | One meeting the caller creates OR attends |
| calls | `references/scopes/calls.md` | 4 | Recipient accepts the call |
| chat | `references/scopes/chat.md` | 29 | CommunicationController_getAiContext |
| collaborations | `references/scopes/collaborations.md` | 10 | CollaborationController_capabilities |
| company-admin | `references/scopes/company-admin.md` | 24 | [Org admin] Set a member's access lifecycle status (pending/approved/r |
| company-admin-excel | `references/scopes/company-admin-excel.md` | 1 | [Org admin] Read-only pre-flight for the import preview |
| company-admin-hawkamah | `references/scopes/company-admin-hawkamah.md` | 2 | This organization's members merged with their Hawkamah governance-exam |
| company-admin-talon | `references/scopes/company-admin-talon.md` | 6 | [Super admin] Correct one Talon user's balance in either direction |
| cost | `references/scopes/cost.md` | 28 | CostController_getCostAccounts |
| cost-categories | `references/scopes/cost-categories.md` | 4 | Create a cost category |
| cost-control | `references/scopes/cost-control.md` | 42 | CostControlController_approveChangeOrder |
| credit-hub | `references/scopes/credit-hub.md` | 4 | Stop reporting this organisation to the hub |
| credits | `references/scopes/credits.md` | 26 | CreditsController_adminAdjust |
| dashboard-widgets | `references/scopes/dashboard-widgets.md` | 5 | Add a widget to a dashboard |
| dashboards | `references/scopes/dashboards.md` | 18 | Create a dashboard |
| data | `references/scopes/data.md` | 1 | Run up to 50 data-proxy reads in one request |
| documents | `references/scopes/documents.md` | 38 | AI-powered document editing |
| email | `references/scopes/email.md` | 52 | EmailController_getAccounts |
| erp | `references/scopes/erp.md` | 2 | ErpReadController_datasets |
| forecast | `references/scopes/forecast.md` | 2 | Daily counts + TimesFM 2 |
| gantt | `references/scopes/gantt.md` | 34 | Activate an approved baseline (snapshot + lock) |
| gis | `references/scopes/gis.md` | 12 | Create multiple zones at once |
| governance | `references/scopes/governance.md` | 77 | GovernanceController_acceptEditRequest |
| graphql | `references/scopes/graphql.md` | 7 | Approve a pending project deletion (human sessions only |
| home | `references/scopes/home.md` | 1 | The personal Home KPI payload for the signed-in user, in their current |
| hr-approval-settings | `references/scopes/hr-approval-settings.md` | 2 | HrApprovalSettingsController_get |
| hr-requests | `references/scopes/hr-requests.md` | 13 | HrRequestsController_myAccess |
| insights | `references/scopes/insights.md` | 9 | Dismiss an insight for the caller |
| invitations | `references/scopes/invitations.md` | 4 | Accept a pending invitation for the calling user |
| lessons | `references/scopes/lessons.md` | 6 | Create a lesson for a project |
| link-preview | `references/scopes/link-preview.md` | 1 | Fetch Open Graph / link-preview metadata for a URL |
| linked-instances | `references/scopes/linked-instances.md` | 14 | Mint a one-time signed hop into a linked deployment |
| material-consumptions | `references/scopes/material-consumptions.md` | 6 | MaterialConsumptionController_available |
| meetings | `references/scopes/meetings.md` | 50 | Create an action item from a rectangle drawn on a shared screen, with  |
| memory | `references/scopes/memory.md` | 9 | memory(action, target, content) |
| misc | `references/scopes/misc.md` | 69 | AgentProfileController_read |
| navigation | `references/scopes/navigation.md` | 1 | Sidebar badge counts for the signed-in user, keyed by nav item |
| notifications | `references/scopes/notifications.md` | 28 | Internal: fan-out low-credit alert to Telegram + Email |
| organizations | `references/scopes/organizations.md` | 13 | Create organization |
| payment-certificates | `references/scopes/payment-certificates.md` | 11 | PaymentCertificateController_approve |
| payments | `references/scopes/payments.md` | 2 | Manually fulfill a pending credit purchase (super-admin only) |
| pdf | `references/scopes/pdf.md` | 4 | PdfController_render |
| plan-generation | `references/scopes/plan-generation.md` | 15 | PlanGenerationController_getActive |
| portfolio | `references/scopes/portfolio.md` | 5 | Create portfolio |
| pre-project | `references/scopes/pre-project.md` | 6 | Create a pre-project initiative (requester = caller) |
| procurement | `references/scopes/procurement.md` | 38 | ProcurementController_aiSuggest |
| procurement-approval-settings | `references/scopes/procurement-approval-settings.md` | 3 | ProcurementApprovalSettingsController_get |
| procurement-plan | `references/scopes/procurement-plan.md` | 5 | ProcurementPlanController_delete |
| procurement-pmo | `references/scopes/procurement-pmo.md` | 6 | ProcurementPmoController_consolidatedDemand |
| procurement-price-anomalies | `references/scopes/procurement-price-anomalies.md` | 8 | ProcurementPriceAnomalyController_check |
| procurement-requests | `references/scopes/procurement-requests.md` | 11 | ProcurementRequestsController_cancel |
| procurement-scoring | `references/scopes/procurement-scoring.md` | 4 | ProcurementScoringController_score |
| program | `references/scopes/program.md` | 10 | Get benefit realization chart data (time-series) |
| project-links | `references/scopes/project-links.md` | 6 | Create project-to-project dependency |
| project-sentiment | `references/scopes/project-sentiment.md` | 1 | Aggregated AI sentiment analysis for all members of a project (team mo |
| projects | `references/scopes/projects.md` | 9 | Delete project (cascades to all child records, scoped to the caller or |
| request-board | `references/scopes/request-board.md` | 19 | Hand a card to someone without moving it between columns |
| risks | `references/scopes/risks.md` | 12 | Get org proactive AI risk detection setting |
| search | `references/scopes/search.md` | 2 | Answer a question about the workspace, with citations |
| sender-pm-approvals | `references/scopes/sender-pm-approvals.md` | 3 | SenderPmApprovalsController_approve |
| snagging | `references/scopes/snagging.md` | 26 | SnaggingAccessController_get |
| storage | `references/scopes/storage.md` | 16 | Abort a multipart upload |
| strategic | `references/scopes/strategic.md` | 57 | Compute KPI achievement percentage |
| strategy | `references/scopes/strategy.md` | 123 | Accept a strategic recommendation |
| strategy-draft | `references/scopes/strategy-draft.md` | 17 | Activate a draft: materialize it as a live, versioned strategy (archiv |
| supplier-evaluations | `references/scopes/supplier-evaluations.md` | 5 | Aggregated rating for a partner across all rated projects |
| system-settings | `references/scopes/system-settings.md` | 4 | Queue every governance row of one organisation for Oravex |
| tasks | `references/scopes/tasks.md` | 23 | Get task comments |
| templates | `references/scopes/templates.md` | 15 | Create a request template from an uploaded file |
| tickets | `references/scopes/tickets.md` | 71 | Accept as suggested, open the backlog item, and optionally assign it |
| time-tracking | `references/scopes/time-tracking.md` | 22 | TimerController_current |
| translate | `references/scopes/translate.md` | 2 | Translate a section name between EN/AR |
| twin | `references/scopes/twin.md` | 6 | TwinPerformanceController_getContactPoint |
| ui-permissions | `references/scopes/ui-permissions.md` | 2 | Caller's effective UI-permission map for one organization, optionally  |
| user-sentiment | `references/scopes/user-sentiment.md` | 1 | Aggregated AI sentiment analysis for a user across meetings, chat mess |
| users | `references/scopes/users.md` | 17 | Get user AI chat quick action suggestions |
| widget-data | `references/scopes/widget-data.md` | 3 | Fetch up to N sample rows for a data source |
| auth | `references/scopes/auth.md` | Restricted | Authentication, recovery, password, OTP, and device-session operations are user-controlled. |
| api-keys | `references/scopes/api-keys.md` | Restricted | API key lifecycle is user-controlled; raw key material must never be exposed to the agent. |

Available to agents: 1614 API commands + 47 core commands across 88 API scopes; authentication, API-key, password-bearing, and account/mailbox deletion operations are withheld.
