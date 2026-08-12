# Tornix command reference — modular index

Commands are split per backend scope. Load ONLY the file matching your task (via skill_view file_path) — do not load the whole tree.

## Core (top-level)
- `references/scopes/core.md` — auth, config, data proxy, projects, tasks, file, meetings, deep-research, rpc, catalog, skill

## API scopes (one file per tag)
| Scope | File | # | Use when |
|---|---|---:|---|
| access-requests | `references/scopes/access-requests.md` | 4 | Approve an access request (super-admin) |
| agile | `references/scopes/agile.md` | 89 | Accept a proposed item for the team |
| ai-agents | `references/scopes/ai-agents.md` | 15 | Cancel a running agent execution |
| ai-chat | `references/scopes/ai-chat.md` | 9 | AiChatController_getAutocompleteSuggestions |
| ai-proxy | `references/scopes/ai-proxy.md` | 76 | AiProxyController_proxyReports_get |
| ai-widgets | `references/scopes/ai-widgets.md` | 6 | Save a generated widget config to the library |
| api-keys | `references/scopes/api-keys.md` | 8 | Create a new API key |
| app-versions | `references/scopes/app-versions.md` | 10 | Re-run AI feature extraction on the release video |
| approvals | `references/scopes/approvals.md` | 52 | Get cached AI review result for a request |
| auth | `references/scopes/auth.md` | 26 | Check if an email address is already registered |
| benefits | `references/scopes/benefits.md` | 7 | Create a benefit |
| bim | `references/scopes/bim.md` | 1 | Resolve the caller's effective BIM permissions for a project |
| calls | `references/scopes/calls.md` | 4 | Recipient accepts the call |
| chat | `references/scopes/chat.md` | 16 | CommunicationController_deleteRoom |
| cost | `references/scopes/cost.md` | 21 | CostController_getCostAccounts |
| cost-categories | `references/scopes/cost-categories.md` | 4 | Create a cost category |
| cost-control | `references/scopes/cost-control.md` | 38 | CostControlController_approveChangeOrder |
| credits | `references/scopes/credits.md` | 23 | CreditsController_adminAdjust |
| dashboard-widgets | `references/scopes/dashboard-widgets.md` | 5 | Add a widget to a dashboard |
| dashboards | `references/scopes/dashboards.md` | 12 | Create a dashboard |
| data | `references/scopes/data.md` | 1 | Run up to 50 data-proxy reads in one request |
| documents | `references/scopes/documents.md` | 16 | AI-powered document editing |
| email | `references/scopes/email.md` | 22 | EmailController_getAccounts |
| gantt | `references/scopes/gantt.md` | 23 | Activate an approved baseline (snapshot + lock) |
| gis | `references/scopes/gis.md` | 12 | Create multiple zones at once |
| governance | `references/scopes/governance.md` | 14 | GovernanceController_listAuthorityLevels |
| hr-approval-settings | `references/scopes/hr-approval-settings.md` | 2 | HrApprovalSettingsController_get |
| hr-requests | `references/scopes/hr-requests.md` | 8 | HrRequestsController_myAccess |
| invitations | `references/scopes/invitations.md` | 4 | Accept a pending invitation for the calling user |
| link-preview | `references/scopes/link-preview.md` | 1 | Fetch Open Graph / link-preview metadata for a URL |
| material-consumptions | `references/scopes/material-consumptions.md` | 5 | MaterialConsumptionController_available |
| meetings | `references/scopes/meetings.md` | 40 | MeetingsController_getActionItems |
| memory | `references/scopes/memory.md` | 9 | memory(action, target, content) |
| misc | `references/scopes/misc.md` | 39 | AiServicesConfigController_read |
| notifications | `references/scopes/notifications.md` | 22 | Internal: fan-out low-credit alert to Telegram + Email |
| organizations | `references/scopes/organizations.md` | 8 | Create organization |
| payment-certificates | `references/scopes/payment-certificates.md` | 11 | PaymentCertificateController_approve |
| payments | `references/scopes/payments.md` | 2 | Manually fulfill a pending credit purchase (super-admin only) |
| pdf | `references/scopes/pdf.md` | 3 | PdfController_render |
| plan-generation | `references/scopes/plan-generation.md` | 14 | PlanGenerationController_getActive |
| portfolio | `references/scopes/portfolio.md` | 5 | Create portfolio |
| pre-project | `references/scopes/pre-project.md` | 6 | Create a pre-project initiative (requester = caller) |
| procurement | `references/scopes/procurement.md` | 37 | ProcurementController_aiSuggest |
| procurement-approval-settings | `references/scopes/procurement-approval-settings.md` | 3 | ProcurementApprovalSettingsController_get |
| procurement-plan | `references/scopes/procurement-plan.md` | 5 | ProcurementPlanController_delete |
| procurement-pmo | `references/scopes/procurement-pmo.md` | 6 | ProcurementPmoController_consolidatedDemand |
| procurement-requests | `references/scopes/procurement-requests.md` | 9 | ProcurementRequestsController_cancel |
| program | `references/scopes/program.md` | 10 | Get benefit realization chart data (time-series) |
| project-links | `references/scopes/project-links.md` | 6 | Create project-to-project dependency |
| project-sentiment | `references/scopes/project-sentiment.md` | 1 | Aggregated AI sentiment analysis for all members of a project (team mo |
| projects | `references/scopes/projects.md` | 9 | Delete project (cascades to all child records, scoped to the caller or |
| request-board | `references/scopes/request-board.md` | 19 | Hand a card to someone without moving it between columns |
| risks | `references/scopes/risks.md` | 11 | Get org proactive AI risk detection setting |
| search | `references/scopes/search.md` | 1 | Fuzzy, typo-tolerant global search across all entities + chat + meetin |
| sender-pm-approvals | `references/scopes/sender-pm-approvals.md` | 3 | SenderPmApprovalsController_approve |
| storage | `references/scopes/storage.md` | 14 | Abort a multipart upload |
| strategic | `references/scopes/strategic.md` | 56 | Compute KPI achievement percentage |
| strategy | `references/scopes/strategy.md` | 104 | Accept a strategic recommendation |
| supplier-evaluations | `references/scopes/supplier-evaluations.md` | 5 | Aggregated rating for a partner across all rated projects |
| system-settings | `references/scopes/system-settings.md` | 3 | Read the effective Odoo bridge config (secrets masked) |
| tasks | `references/scopes/tasks.md` | 16 | Get task comments |
| templates | `references/scopes/templates.md` | 15 | Create a request template from an uploaded file |
| tickets | `references/scopes/tickets.md` | 51 | Accept as suggested, open the backlog item, and optionally assign it |
| time-tracking | `references/scopes/time-tracking.md` | 21 | TimerController_current |
| translate | `references/scopes/translate.md` | 2 | Translate a section name between EN/AR |
| twin | `references/scopes/twin.md` | 1 | Every dataset the Twin page needs, in one request |
| user-sentiment | `references/scopes/user-sentiment.md` | 1 | Aggregated AI sentiment analysis for a user across meetings, chat mess |
| users | `references/scopes/users.md` | 17 | Get user AI chat quick action suggestions |
| widget-data | `references/scopes/widget-data.md` | 3 | Fetch up to N sample rows for a data source |

Total: 1122 api commands + 45 core commands across 69 scopes.
