# Final product feature inventory

Source reconciliation and current acceptance; open rows remain explicit

No inherited completion percentages or historical VERIFIED labels become VERIFIED LIVE. Static elements are code surfaces only, not functional acceptance. PARTIAL requirement rows explicitly remain unassessed at subfeature level.

Starting commit: `e8ff078dc356653873d2f26de4d0563dd3ff7096`

Exact inventory denominator: **1839 records**. Mandatory requirement rows and static technical surfaces are separate kinds; do not count them as unique completed customer capabilities.

| Status | Records |
|---|---:|
| VERIFIED LIVE | 0 |
| IMPLEMENTED / NOT VERIFIED | 1242 |
| BROKEN | 6 |
| PARTIAL | 296 |
| MISSING | 0 |
| EXTERNALLY BLOCKED | 14 |
| INTENTIONALLY HIDDEN | 281 |
| NOT APPLICABLE | 0 |

All required metadata, source locations and provisional reasons are in the JSON. Regex control enumeration is a discovery aid, not a complete JSX/dataflow proof. Dynamic routes and handler links still need reconciliation.

| ID | Requirement | Initial status | Source |
|---|---|---|---|
| A.01 | Google sign-in | PARTIAL | app/platform/admission.py |
| A.02 | Session creation | PARTIAL | app/platform/admission.py |
| A.03 | Session refresh | PARTIAL | app/platform/admission.py |
| A.04 | Sign-out | PARTIAL | app/platform/admission.py |
| A.05 | Unauthorized-access handling | PARTIAL | app/platform/admission.py |
| A.06 | Approved account registration | PARTIAL | app/platform/admission.py |
| A.07 | New account creation | INTENTIONALLY HIDDEN | app/platform/admission.py |
| A.08 | Existing account recovery | PARTIAL | app/platform/admission.py |
| A.09 | Personal profile display | PARTIAL | app/platform/admission.py |
| A.10 | Profile editing | PARTIAL | app/platform/admission.py |
| A.11 | Display-name persistence | PARTIAL | app/platform/admission.py |
| A.12 | Timezone preference | PARTIAL | app/platform/admission.py |
| A.13 | Language preference | PARTIAL | app/platform/admission.py |
| A.14 | Appearance preference | PARTIAL | app/platform/admission.py |
| A.15 | Security settings | PARTIAL | app/platform/admission.py |
| A.16 | Account/workspace separation | PARTIAL | app/platform/admission.py |
| A.17 | Authentication errors and recovery | PARTIAL | app/platform/admission.py |
| B.01 | Workspace creation | PARTIAL | app/api/organization.py |
| B.02 | Workspace selection | PARTIAL | app/api/organization.py |
| B.03 | Organization profile | PARTIAL | app/api/organization.py |
| B.04 | Organization-domain configuration | PARTIAL | app/api/organization.py |
| B.05 | Business offering description | PARTIAL | app/api/organization.py |
| B.06 | Industry and market context | PARTIAL | app/api/organization.py |
| B.07 | ICP creation | PARTIAL | app/api/organization.py |
| B.08 | ICP editing | PARTIAL | app/api/organization.py |
| B.09 | ICP selection | PARTIAL | app/api/organization.py |
| B.10 | Team member list | PARTIAL | app/api/organization.py |
| B.11 | Invitations | PARTIAL | app/api/organization.py |
| B.12 | Invite acceptance | PARTIAL | app/api/organization.py |
| B.13 | Role assignments | PARTIAL | app/api/organization.py |
| B.14 | Permission enforcement | PARTIAL | app/api/organization.py |
| B.15 | Workspace switching | PARTIAL | app/api/organization.py |
| B.16 | Member removal | PARTIAL | app/api/organization.py |
| B.17 | Tenant isolation | PARTIAL | app/api/organization.py |
| B.18 | Workspace audit history | PARTIAL | app/api/organization.py |
| C.01 | First-run onboarding | PARTIAL | app/platform/onboarding.py |
| C.02 | Progress persistence | PARTIAL | app/platform/onboarding.py |
| C.03 | Optional-step skipping | PARTIAL | app/platform/onboarding.py |
| C.04 | Company setup | PARTIAL | app/platform/onboarding.py |
| C.05 | Ideal customer setup | PARTIAL | app/platform/onboarding.py |
| C.06 | Source explanation | PARTIAL | app/platform/onboarding.py |
| C.07 | First research brief | PARTIAL | app/platform/onboarding.py |
| C.08 | First successful search | PARTIAL | app/platform/onboarding.py |
| C.09 | First signal review | PARTIAL | app/platform/onboarding.py |
| C.10 | First save | PARTIAL | app/platform/onboarding.py |
| C.11 | First monitor creation | PARTIAL | app/platform/onboarding.py |
| C.12 | Contextual guidance | PARTIAL | app/platform/onboarding.py |
| C.13 | Onboarding completion | PARTIAL | app/platform/onboarding.py |
| D.01 | Consistent navigation | PARTIAL | app/api/security.py |
| D.02 | Collapsible sidebar | PARTIAL | app/api/security.py |
| D.03 | Mobile navigation | PARTIAL | app/api/security.py |
| D.04 | Useful page headers | PARTIAL | app/api/security.py |
| D.05 | Unified search behavior | PARTIAL | app/api/security.py |
| D.06 | Breadcrumbs where needed | PARTIAL | app/api/security.py |
| D.07 | Responsive data tables | PARTIAL | app/api/security.py |
| D.08 | Correct content widths | PARTIAL | app/api/security.py |
| D.09 | Compact forms | PARTIAL | app/api/security.py |
| D.10 | Accessible dropdowns | PARTIAL | app/api/security.py |
| D.11 | Consistent dialogs | PARTIAL | app/api/security.py |
| D.12 | Functional toast messages | PARTIAL | app/api/security.py |
| D.13 | Keyboard navigation | PARTIAL | app/api/security.py |
| D.14 | Screen-reader accessibility | PARTIAL | app/api/security.py |
| D.15 | Empty states | PARTIAL | app/api/security.py |
| D.16 | Loading states | PARTIAL | app/api/security.py |
| D.17 | Error states | PARTIAL | app/api/security.py |
| D.18 | Retry behavior | PARTIAL | app/api/security.py |
| D.19 | No horizontal clipping | PARTIAL | app/api/security.py |
| D.20 | No stuck loading skeletons | PARTIAL | app/api/security.py |
| D.21 | No broken browser-back navigation | PARTIAL | app/api/security.py |
| D.22 | No dead buttons | PARTIAL | app/api/security.py |
| D.23 | No duplicated or misleading navigation | PARTIAL | app/api/security.py |
| E.01 | Natural-language discovery | PARTIAL | app/intent_radar/discovery.py |
| E.02 | Advanced keyword search | PARTIAL | app/intent_radar/discovery.py |
| E.03 | Topic filters | PARTIAL | app/intent_radar/discovery.py |
| E.04 | Intent phrase filters | PARTIAL | app/intent_radar/discovery.py |
| E.05 | Exclusion filters | PARTIAL | app/intent_radar/discovery.py |
| E.06 | Relevant offerings | PARTIAL | app/intent_radar/discovery.py |
| E.07 | ICP-based search | PARTIAL | app/intent_radar/discovery.py |
| E.08 | Source selection | PARTIAL | app/intent_radar/discovery.py |
| E.09 | Time-window filtering | PARTIAL | app/intent_radar/discovery.py |
| E.10 | Supported language filtering | PARTIAL | app/intent_radar/discovery.py |
| E.11 | Search criteria preview | PARTIAL | app/intent_radar/discovery.py |
| E.12 | Search initiation | PARTIAL | app/intent_radar/discovery.py |
| E.13 | Search progress | PARTIAL | app/intent_radar/discovery.py |
| E.14 | Source-level job status | PARTIAL | app/intent_radar/discovery.py |
| E.15 | Partial-source failure handling | PARTIAL | app/intent_radar/discovery.py |
| E.16 | Results pagination | PARTIAL | app/intent_radar/discovery.py |
| E.17 | Search history | PARTIAL | app/intent_radar/discovery.py |
| E.18 | Saved searches | PARTIAL | app/intent_radar/discovery.py |
| E.19 | Relevant sorting | PARTIAL | app/intent_radar/discovery.py |
| E.20 | Search usage accounting | PARTIAL | app/intent_radar/discovery.py |
| E.21 | Cancel/retry | PARTIAL | app/intent_radar/discovery.py |
| E.22 | Reliable real-source results | PARTIAL | app/intent_radar/discovery.py |
| F.01 | Hacker News live requests | PARTIAL | app/intent_radar/connectors.py |
| F.02 | Hacker News feed options | PARTIAL | app/intent_radar/connectors.py |
| F.03 | Hacker News comment controls | PARTIAL | app/intent_radar/connectors.py |
| F.04 | Stack Exchange API integration | PARTIAL | app/intent_radar/connectors.py |
| F.05 | Stack Exchange key configuration | PARTIAL | app/intent_radar/connectors.py |
| F.06 | Stack Exchange permission evidence | EXTERNALLY BLOCKED | app/intent_radar/connectors.py |
| F.07 | Discourse endpoint configuration | PARTIAL | app/intent_radar/connectors.py |
| F.08 | Discourse publisher terms | EXTERNALLY BLOCKED | app/intent_radar/connectors.py |
| F.09 | RSS/Atom endpoint configuration | PARTIAL | app/intent_radar/connectors.py |
| F.10 | RSS publisher terms | EXTERNALLY BLOCKED | app/intent_radar/connectors.py |
| F.11 | Host allowlisting | PARTIAL | app/intent_radar/connectors.py |
| F.12 | Feed validation | PARTIAL | app/intent_radar/connectors.py |
| F.13 | Attribution | PARTIAL | app/intent_radar/connectors.py |
| F.14 | Source health | PARTIAL | app/intent_radar/connectors.py |
| F.15 | Source quota handling | PARTIAL | app/intent_radar/connectors.py |
| F.16 | Incremental cursors | PARTIAL | app/intent_radar/connectors.py |
| F.17 | Pagination | PARTIAL | app/intent_radar/connectors.py |
| F.18 | Retry and backoff | PARTIAL | app/intent_radar/connectors.py |
| F.19 | Cross-source deduplication | PARTIAL | app/intent_radar/connectors.py |
| F.20 | Retention enforcement | PARTIAL | app/intent_radar/connectors.py |
| F.21 | Accurate availability labels | PARTIAL | app/intent_radar/connectors.py |
| G.01 | Signal list | PARTIAL | app/intent_radar/intelligence.py |
| G.02 | Signal detail | PARTIAL | app/intent_radar/intelligence.py |
| G.03 | Original source links | PARTIAL | app/intent_radar/intelligence.py |
| G.04 | Exact excerpts | PARTIAL | app/intent_radar/intelligence.py |
| G.05 | Source timestamps | PARTIAL | app/intent_radar/intelligence.py |
| G.06 | Intent classification | PARTIAL | app/intent_radar/intelligence.py |
| G.07 | Relevance scoring | PARTIAL | app/intent_radar/intelligence.py |
| G.08 | Buyer-need explanation | PARTIAL | app/intent_radar/intelligence.py |
| G.09 | ICP fit | PARTIAL | app/intent_radar/intelligence.py |
| G.10 | Negative evidence | PARTIAL | app/intent_radar/intelligence.py |
| G.11 | Confidence and uncertainty | PARTIAL | app/intent_radar/intelligence.py |
| G.12 | Feedback | PARTIAL | app/intent_radar/intelligence.py |
| G.13 | Feedback impact on ranking | PARTIAL | app/intent_radar/intelligence.py |
| G.14 | Save and unsave | PARTIAL | app/intent_radar/intelligence.py |
| G.15 | Dismiss and restore | PARTIAL | app/intent_radar/intelligence.py |
| G.16 | Related discussions | PARTIAL | app/intent_radar/intelligence.py |
| G.17 | Filtering | PARTIAL | app/intent_radar/intelligence.py |
| G.18 | Sorting | PARTIAL | app/intent_radar/intelligence.py |
| G.19 | Pagination | PARTIAL | app/intent_radar/intelligence.py |
| G.20 | Signal-to-opportunity conversion | IMPLEMENTED / NOT VERIFIED | app/intent_radar/intelligence.py |
| H.01 | Opportunity creation | PARTIAL | app/intent_radar/service.py |
| H.02 | Qualification criteria | IMPLEMENTED / NOT VERIFIED | app/intent_radar/service.py |
| H.03 | Status management | PARTIAL | app/intent_radar/service.py |
| H.04 | Priority management | PARTIAL | app/intent_radar/service.py |
| H.05 | Evidence linking | PARTIAL | app/intent_radar/service.py |
| H.06 | Opportunity notes | PARTIAL | app/intent_radar/service.py |
| H.07 | Next actions | PARTIAL | app/intent_radar/service.py |
| H.08 | Reviewer assignment | PARTIAL | app/intent_radar/service.py |
| H.09 | Activity history | PARTIAL | app/intent_radar/service.py |
| H.10 | Duplicate handling | PARTIAL | app/intent_radar/service.py |
| H.11 | List filtering | PARTIAL | app/intent_radar/service.py |
| H.12 | Sorting | PARTIAL | app/intent_radar/service.py |
| H.13 | Full detail view | PARTIAL | app/intent_radar/service.py |
| H.14 | Status persistence | PARTIAL | app/intent_radar/service.py |
| H.15 | Empty states | PARTIAL | app/intent_radar/service.py |
| H.16 | Incorrect-opportunity feedback | PARTIAL | app/intent_radar/service.py |
| I.01 | Create monitor | PARTIAL | app/intent_radar/schedules.py |
| I.02 | Create from search | PARTIAL | app/intent_radar/schedules.py |
| I.03 | Configure cadence | PARTIAL | app/intent_radar/schedules.py |
| I.04 | Select sources | PARTIAL | app/intent_radar/schedules.py |
| I.05 | Monitor activation | PARTIAL | app/intent_radar/schedules.py |
| I.06 | Pause and resume | PARTIAL | app/intent_radar/schedules.py |
| I.07 | Archive | PARTIAL | app/intent_radar/schedules.py |
| I.08 | Scheduled worker execution | PARTIAL | app/intent_radar/schedules.py |
| I.09 | Run history | PARTIAL | app/intent_radar/schedules.py |
| I.10 | Next-run display | PARTIAL | app/intent_radar/schedules.py |
| I.11 | Last-successful-run display | PARTIAL | app/intent_radar/schedules.py |
| I.12 | Incremental collection | PARTIAL | app/intent_radar/schedules.py |
| I.13 | Retry and recovery | PARTIAL | app/intent_radar/schedules.py |
| I.14 | Source-specific failures | PARTIAL | app/intent_radar/schedules.py |
| I.15 | Deduplicated matches | PARTIAL | app/intent_radar/schedules.py |
| I.16 | In-app alerts | PARTIAL | app/intent_radar/schedules.py |
| I.17 | Usage enforcement | PARTIAL | app/intent_radar/schedules.py |
| I.18 | Worker observability | PARTIAL | app/intent_radar/schedules.py |
| J.01 | Market overview | PARTIAL | app/growth_intelligence/service.py |
| J.02 | Data-coverage visibility | PARTIAL | app/growth_intelligence/service.py |
| J.03 | Market themes | PARTIAL | app/growth_intelligence/service.py |
| J.04 | Theme evidence | PARTIAL | app/growth_intelligence/service.py |
| J.05 | Conversation trends | PARTIAL | app/growth_intelligence/service.py |
| J.06 | Time comparison | PARTIAL | app/growth_intelligence/service.py |
| J.07 | Insufficient-data handling | PARTIAL | app/growth_intelligence/service.py |
| J.08 | Buyer problem summaries | PARTIAL | app/growth_intelligence/service.py |
| J.09 | Market opportunity explanations | PARTIAL | app/growth_intelligence/service.py |
| J.10 | Competitor creation | PARTIAL | app/growth_intelligence/service.py |
| J.11 | Competitor aliases | PARTIAL | app/growth_intelligence/service.py |
| J.12 | Competitor disambiguation | PARTIAL | app/growth_intelligence/service.py |
| J.13 | Competitor mentions | PARTIAL | app/growth_intelligence/service.py |
| J.14 | Alternatives/comparisons | PARTIAL | app/growth_intelligence/service.py |
| J.15 | Competitor watchlists | PARTIAL | app/growth_intelligence/service.py |
| J.16 | Research assistant | PARTIAL | app/growth_intelligence/service.py |
| J.17 | Saved research | PARTIAL | app/growth_intelligence/service.py |
| J.18 | Research reports | PARTIAL | app/growth_intelligence/service.py |
| J.19 | Citation integrity | PARTIAL | app/growth_intelligence/service.py |
| J.20 | Research export | PARTIAL | app/growth_intelligence/service.py |
| J.21 | Insight-to-source navigation | PARTIAL | app/growth_intelligence/service.py |
| K.01 | Assistant availability | PARTIAL | app/intent_radar/assistant.py |
| K.02 | Greeting and basic guidance | IMPLEMENTED / NOT VERIFIED | app/intent_radar/assistant.py |
| K.03 | Accurate workspace counts | IMPLEMENTED / NOT VERIFIED | app/intent_radar/assistant_reads.py |
| K.04 | Accurate quota answers | IMPLEMENTED / NOT VERIFIED | app/intent_radar/assistant_reads.py |
| K.05 | Relevant contextual answers | PARTIAL | app/intent_radar/assistant.py |
| K.06 | Persistent conversation | IMPLEMENTED / NOT VERIFIED | app/intent_radar/assistant.py |
| K.07 | Multi-turn follow-up | IMPLEMENTED / NOT VERIFIED | app/intent_radar/assistant.py |
| K.08 | Safe tool routing | IMPLEMENTED / NOT VERIFIED | app/intent_radar/assistant_reads.py |
| K.09 | Evidence retrieval | PARTIAL | app/intent_radar/assistant.py |
| K.10 | Grounded generation | PARTIAL | app/intent_radar/assistant.py |
| K.11 | Vertex AI service access | PARTIAL | app/intent_radar/assistant.py |
| K.12 | Correct model selection | PARTIAL | app/intent_radar/assistant.py |
| K.13 | Provider timeouts | IMPLEMENTED / NOT VERIFIED | app/intent_radar/assistant.py |
| K.14 | Error messages | IMPLEMENTED / NOT VERIFIED | app/intent_radar/assistant.py |
| K.15 | Retry and fallback | IMPLEMENTED / NOT VERIFIED | app/intent_radar/assistant.py |
| K.16 | Request accounting | IMPLEMENTED / NOT VERIFIED | app/intent_radar/assistant.py |
| K.17 | Token accounting | IMPLEMENTED / NOT VERIFIED | app/intent_radar/assistant.py |
| K.18 | Reservation release | IMPLEMENTED / NOT VERIFIED | app/intent_radar/assistant.py |
| K.19 | Conversation isolation | IMPLEMENTED / NOT VERIFIED | app/intent_radar/assistant.py |
| K.20 | AI evaluation | EXTERNALLY BLOCKED | app/intent_radar/assistant.py |
| K.21 | Hallucination controls | PARTIAL | app/intent_radar/assistant.py |
| K.22 | Human evaluation evidence | EXTERNALLY BLOCKED | app/intent_radar/assistant.py |
| L.01 | Save signal | PARTIAL | app/intent_radar/service.py |
| L.02 | Unsave signal | PARTIAL | app/intent_radar/service.py |
| L.03 | Collections | PARTIAL | app/intent_radar/service.py |
| L.04 | Collection filtering | PARTIAL | app/intent_radar/service.py |
| L.05 | Notes | PARTIAL | app/intent_radar/service.py |
| L.06 | Tags | PARTIAL | app/intent_radar/service.py |
| L.07 | Search saved content | PARTIAL | app/intent_radar/service.py |
| L.08 | Sorting | PARTIAL | app/intent_radar/service.py |
| L.09 | Saved reports | PARTIAL | app/intent_radar/service.py |
| L.10 | Reopen reports | PARTIAL | app/intent_radar/service.py |
| L.11 | Export reports | PARTIAL | app/intent_radar/service.py |
| L.12 | Source preservation | PARTIAL | app/intent_radar/service.py |
| L.13 | Retention handling | PARTIAL | app/intent_radar/service.py |
| L.14 | Authorization | PARTIAL | app/intent_radar/service.py |
| L.15 | Empty-state guidance | PARTIAL | app/intent_radar/service.py |
| M.01 | Alert generation | PARTIAL | app/intent_radar/service.py |
| M.02 | Unread count | PARTIAL | app/intent_radar/service.py |
| M.03 | Read/unread persistence | PARTIAL | app/intent_radar/service.py |
| M.04 | Monitor match links | PARTIAL | app/intent_radar/service.py |
| M.05 | Source failure links | PARTIAL | app/intent_radar/service.py |
| M.06 | Preference configuration | PARTIAL | app/intent_radar/service.py |
| M.07 | Priority thresholds | PARTIAL | app/intent_radar/service.py |
| M.08 | Pagination | PARTIAL | app/intent_radar/service.py |
| M.09 | Deduplication | PARTIAL | app/intent_radar/service.py |
| M.10 | Notification accessibility | PARTIAL | app/intent_radar/service.py |
| M.11 | Correct permission enforcement | PARTIAL | app/intent_radar/service.py |
| N.01 | Connection catalog | PARTIAL | app/developer/mcp_server.py |
| N.02 | Accurate source connection states | PARTIAL | app/developer/mcp_server.py |
| N.03 | API key creation | PARTIAL | app/developer/mcp_server.py |
| N.04 | Key expiration | PARTIAL | app/developer/mcp_server.py |
| N.05 | Key revocation | PARTIAL | app/developer/mcp_server.py |
| N.06 | Key scopes | PARTIAL | app/developer/mcp_server.py |
| N.07 | MCP endpoint | IMPLEMENTED / NOT VERIFIED | app/developer/mcp_server.py |
| N.08 | MCP authentication | IMPLEMENTED / NOT VERIFIED | app/developer/mcp_server.py |
| N.09 | MCP tool discovery | IMPLEMENTED / NOT VERIFIED | app/developer/mcp_server.py |
| N.10 | MCP real client acceptance | IMPLEMENTED / NOT VERIFIED | app/developer/mcp_server.py |
| N.11 | Workspace isolation | PARTIAL | app/developer/mcp_server.py |
| N.12 | MCP usage accounting | PARTIAL | app/developer/mcp_server.py |
| N.13 | API rate limiting | PARTIAL | app/developer/mcp_server.py |
| N.14 | API documentation | PARTIAL | app/developer/mcp_server.py |
| N.15 | Error diagnostics | PARTIAL | app/developer/mcp_server.py |
| N.16 | Accurate integration status labeling | PARTIAL | app/developer/mcp_server.py |
| O.01 | Current entitlement | PARTIAL | app/billing/service.py |
| O.02 | Current paid plan | PARTIAL | app/billing/service.py |
| O.03 | Beta-vs-paid distinction | PARTIAL | app/billing/service.py |
| O.04 | Approved price display | IMPLEMENTED / NOT VERIFIED | app/billing/service.py |
| O.05 | Plan comparison | IMPLEMENTED / NOT VERIFIED | app/billing/service.py |
| O.06 | Monthly allowances | IMPLEMENTED / NOT VERIFIED | app/billing/service.py |
| O.07 | Upgrade/downgrade presentation | PARTIAL | app/billing/service.py |
| O.08 | Subscription details | PARTIAL | app/billing/service.py |
| O.09 | Payment gateway availability | PARTIAL | app/billing/service.py |
| O.10 | PayU merchant configuration | PARTIAL | app/billing/service.py |
| O.11 | PayU recurring capabilities | EXTERNALLY BLOCKED | app/billing/service.py |
| O.12 | Payment verification | EXTERNALLY BLOCKED | app/billing/service.py |
| O.13 | Webhook verification | EXTERNALLY BLOCKED | app/billing/service.py |
| O.14 | Renewal lifecycle | EXTERNALLY BLOCKED | app/billing/service.py |
| O.15 | Cancellation | EXTERNALLY BLOCKED | app/billing/service.py |
| O.16 | Refund lifecycle | EXTERNALLY BLOCKED | app/billing/service.py |
| O.17 | Billing history | PARTIAL | app/billing/service.py |
| O.18 | Historical provider labeling | IMPLEMENTED / NOT VERIFIED | app/billing/service.py |
| O.19 | Test-mode separation | IMPLEMENTED / NOT VERIFIED | app/billing/service.py |
| O.20 | Customer-facing invoices/receipts where supported | PARTIAL | app/billing/service.py |
| O.21 | Marketing pricing synchronization | IMPLEMENTED / NOT VERIFIED | app/billing/service.py |
| P.01 | Monthly search accounting | PARTIAL | app/billing/commercial_usage.py |
| P.02 | Daily search safety caps | PARTIAL | app/billing/commercial_usage.py |
| P.03 | Shared AI operations | IMPLEMENTED / NOT VERIFIED | app/billing/commercial_usage.py |
| P.04 | AI token reservation | IMPLEMENTED / NOT VERIFIED | app/billing/commercial_usage.py |
| P.05 | Actual provider token accounting | IMPLEMENTED / NOT VERIFIED | app/billing/commercial_usage.py |
| P.06 | Reports allowance | IMPLEMENTED / NOT VERIFIED | app/billing/commercial_usage.py |
| P.07 | Monitor allowance | PARTIAL | app/billing/commercial_usage.py |
| P.08 | API/MCP allowance | PARTIAL | app/billing/commercial_usage.py |
| P.09 | Seat allowance | PARTIAL | app/billing/commercial_usage.py |
| P.10 | Concurrent reservation correctness | IMPLEMENTED / NOT VERIFIED | app/billing/commercial_usage.py |
| P.11 | Failed-job refunds | IMPLEMENTED / NOT VERIFIED | app/billing/commercial_usage.py |
| P.12 | Background-job accounting | IMPLEMENTED / NOT VERIFIED | app/billing/commercial_usage.py |
| P.13 | Scheduled-job accounting | PARTIAL | app/billing/commercial_usage.py |
| P.14 | Reset windows | PARTIAL | app/billing/commercial_usage.py |
| P.15 | Usage display accuracy | PARTIAL | app/billing/commercial_usage.py |
| P.16 | Low-usage warnings | PARTIAL | app/billing/commercial_usage.py |
| P.17 | Limit exhaustion messaging | PARTIAL | app/billing/commercial_usage.py |
| P.18 | Server-side feature locking | PARTIAL | app/billing/commercial_usage.py |
| P.19 | Plan-specific entitlement enforcement | PARTIAL | app/billing/commercial_usage.py |
| P.20 | Upgrade guidance without forced checkout | PARTIAL | app/billing/commercial_usage.py |
| P.21 | Workspace-scoped quota isolation | IMPLEMENTED / NOT VERIFIED | app/billing/commercial_usage.py |
| Q.01 | Fast authentication | PARTIAL | app/database/postgres.py |
| Q.02 | Fast overview | BROKEN | app/database/postgres.py |
| Q.03 | Fast discovery-page readiness | PARTIAL | app/database/postgres.py |
| Q.04 | Fast signal list | BROKEN | app/database/postgres.py |
| Q.05 | Fast opportunities | BROKEN | app/database/postgres.py |
| Q.06 | Fast Growth Intelligence | BROKEN | app/database/postgres.py |
| Q.07 | Fast billing page | BROKEN | app/database/postgres.py |
| Q.08 | Fast settings | BROKEN | app/database/postgres.py |
| Q.09 | Bounded AI request time | PARTIAL | app/database/postgres.py |
| Q.10 | Responsive background jobs | PARTIAL | app/database/postgres.py |
| Q.11 | Database indexing | PARTIAL | app/database/postgres.py |
| Q.12 | N+1 query elimination | PARTIAL | app/database/postgres.py |
| Q.13 | Connection pooling | PARTIAL | app/database/postgres.py |
| Q.14 | Cache correctness | PARTIAL | app/database/postgres.py |
| Q.15 | Cache tenant isolation | PARTIAL | app/database/postgres.py |
| Q.16 | Page pagination | PARTIAL | app/database/postgres.py |
| Q.17 | Bundle optimization | PARTIAL | app/database/postgres.py |
| Q.18 | Responsive rendering | PARTIAL | app/database/postgres.py |
| Q.19 | Cold-start mitigation | PARTIAL | app/database/postgres.py |
| Q.20 | p50 and p95 measurements | PARTIAL | app/database/postgres.py |
| Q.21 | Load testing | PARTIAL | app/database/postgres.py |
| Q.22 | Error-rate monitoring | PARTIAL | app/database/postgres.py |
| R.01 | Workspace access isolation | IMPLEMENTED / NOT VERIFIED | app/api/security.py |
| R.02 | Role-based authorization | IMPLEMENTED / NOT VERIFIED | app/api/security.py |
| R.03 | Direct API authorization | IMPLEMENTED / NOT VERIFIED | app/api/security.py |
| R.04 | Feature entitlement enforcement | IMPLEMENTED / NOT VERIFIED | app/api/security.py |
| R.05 | Secrets kept server-side | PARTIAL | app/api/security.py |
| R.06 | Signed worker requests | IMPLEMENTED / NOT VERIFIED | app/api/security.py |
| R.07 | Secure MCP credentials | IMPLEMENTED / NOT VERIFIED | app/api/security.py |
| R.08 | Webhook authentication | PARTIAL | app/api/security.py |
| R.09 | Feed SSRF protection | IMPLEMENTED / NOT VERIFIED | app/api/security.py |
| R.10 | Request rate limiting | IMPLEMENTED / NOT VERIFIED | app/api/security.py |
| R.11 | Data encryption where required | PARTIAL | app/api/security.py |
| R.12 | Audit logging | IMPLEMENTED / NOT VERIFIED | app/api/security.py |
| R.13 | Backup verification | IMPLEMENTED / NOT VERIFIED | app/api/security.py |
| R.14 | Restore rehearsal | IMPLEMENTED / NOT VERIFIED | app/api/security.py |
| R.15 | Safe migrations | IMPLEMENTED / NOT VERIFIED | app/api/security.py |
| R.16 | Rollback readiness | PARTIAL | app/api/security.py |
| R.17 | Worker health monitoring | PARTIAL | app/api/security.py |
| R.18 | Production error tracking | PARTIAL | app/api/security.py |
| R.19 | Release monitoring | PARTIAL | app/api/security.py |
| R.20 | Source permission records | PARTIAL | app/api/security.py |
| R.21 | Retention enforcement | IMPLEMENTED / NOT VERIFIED | app/api/security.py |
| S.01 | New user onboarding | PARTIAL | scripts/deploy_product_release.py |
| S.02 | Approved second-account acceptance | PARTIAL | scripts/deploy_product_release.py |
| S.03 | First real search | PARTIAL | scripts/deploy_product_release.py |
| S.04 | First signal saved | PARTIAL | scripts/deploy_product_release.py |
| S.05 | First opportunity qualified | PARTIAL | scripts/deploy_product_release.py |
| S.06 | First monitor run | PARTIAL | scripts/deploy_product_release.py |
| S.07 | First alert opened | PARTIAL | scripts/deploy_product_release.py |
| S.08 | First Growth Intelligence report | PARTIAL | scripts/deploy_product_release.py |
| S.09 | First exported report | PARTIAL | scripts/deploy_product_release.py |
| S.10 | Multi-turn AI assistant conversation | PARTIAL | scripts/deploy_product_release.py |
| S.11 | Real external MCP read | IMPLEMENTED / NOT VERIFIED | scripts/deploy_product_release.py |
| S.12 | Billing usage accuracy | PARTIAL | scripts/deploy_product_release.py |
| S.13 | Proper quota exhaustion | PARTIAL | scripts/deploy_product_release.py |
| S.14 | Team and settings persistence | PARTIAL | scripts/deploy_product_release.py |
| S.15 | Desktop browser acceptance | PARTIAL | scripts/deploy_product_release.py |
| S.16 | Tablet acceptance | PARTIAL | scripts/deploy_product_release.py |
| S.17 | Mobile acceptance | PARTIAL | scripts/deploy_product_release.py |
| S.18 | Keyboard accessibility | PARTIAL | scripts/deploy_product_release.py |
| S.19 | Screen-reader accessibility | PARTIAL | scripts/deploy_product_release.py |
| S.20 | No critical browser errors | PARTIAL | scripts/deploy_product_release.py |
| S.21 | Production version verification | PARTIAL | scripts/deploy_product_release.py |
| S.22 | Rollback rehearsal | PARTIAL | scripts/deploy_product_release.py |
| S.23 | Final owner walkthrough | PARTIAL | scripts/deploy_product_release.py |
