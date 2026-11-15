# PlaneByte information architecture

## Main navigation

| Group | Destination | Existing implementation preserved |
|---|---|---|
| Workspace | Home | Progressive overview summary and recent evidence |
| Workspace | Discover | Describe → review → explicit bounded search |
| Workspace | Signals | Filters, table/cards, evidence drawer and persisted actions |
| Workspace | Opportunities | Evidence admission, priorities, review and notes |
| Workspace | Monitoring | Drafts, explicit checks, schedules, cancellation and history |
| Intelligence | Growth Intelligence | Contextual market/themes/trends/competitor/research/watchlist/report tabs |
| Intelligence | Intelligence Graph | Shared company context, topics, competitors and monitors |
| Intelligence | Research Library | Existing saved signals; Growth tabs retain saved research and reports |
| Platform | AI Assistant | Focused conversation using the existing private assistant |
| Platform | Connections | Actual data sources, scoped MCP, native alerts, clearly planned providers |
| Platform | Usage & Billing | Current access first, usage, then optional approved plan comparison |
| Bottom | Settings / Help | Unified settings navigation and existing documentation |

Growth and Assistant navigation require the existing Growth entitlement. Lead Engine navigation remains absent when its launch flag is false; its source, APIs, data, tests and future activation path are preserved.

## Settings destinations

Account → `/account/profile`; Company → `/settings/company`; Ideal customers → `/settings/icp`; Connected accounts → `/intent-radar/integrations`; Team → `/settings/members`; Sources & preferences → `/intent-radar/settings`; Billing → `/billing`; Developer → `/settings/developer` when permitted; Security → `/account/security`; Domains → `/settings/domains`.

Existing direct links and server guards remain valid. Desktop settings use one two-pane frame; mobile categories remain reachable without fixed-width overflow. Connected accounts leads to the actual catalog, since a catalog entry does not establish a connected identity.

## Consolidation decisions

Growth's eight sidebar entries move into contextual tabs. Duplicate Radar/workspace settings links become one Settings entry. Home owns workspace counts and the AI entry. The graph reads and writes the same company profile used by setup and research; it does not create another business-profile store. Signal review opens locally without discarding list state, while deep links still work.
