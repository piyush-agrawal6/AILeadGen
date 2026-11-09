# Campaign-centric operations upgrade — delivered for review

Preserve data, existing scan/mail/report/tracking/reply/bounce/scheduler engines and current false flags. No real scans or mail during QA.

1. Shared dense page/list shell, status badges, sortable/paginated tables, sticky filter/search bars and reusable drawers.
2. One campaign audience/accounting function used by campaign actions, Outreach and scheduled combined runs. Mandatory campaign/pitch selection, no email count, disjoint accounting and explicit safe re-contact.
3. Minimal additive campaign linkage and safe legacy schedule-intent migration; preserve historical scans/messages and existing schedule rows. No duplicate lead/campaign tables.
4. Apply operational pages to Dashboard, Leads/saved views, Campaigns, Outreach, Schedules, Reports and Settings with real data and appropriate server-side filters/counts.
5. Unit, disposable PostgreSQL, browser/responsive/visual regression checks; guarded deployment only after checks pass. All acquisition/outreach remains paused for owner review. No acceptance email requested this pass.

Review release verified on 2026-11-01. See `CAMPAIGN_OPERATIONS_IMPLEMENTATION.md` and `CAMPAIGN_OPERATIONS_DEPLOYMENT_STATE.json`. Production activation remains owner-controlled and disabled.
