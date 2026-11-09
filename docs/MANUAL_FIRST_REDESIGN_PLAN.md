# Active implementation scope

Implement both owner briefs, preserving data and existing mail/scan infrastructure.

1. Shared evidence-led commercial content plan, four deterministic email variants, 8-page premium opportunity PDF, approved offer/service selection, simplified signature and subtle unsubscribe.
2. Fail-closed content/PDF gates and exact final HTML/text/attachment previews; edit, regenerate, view/download.
3. Additive PostgreSQL workflow runs/items and user schedules/history. Existing scan executor and reviewed mail service remain execution primitives. Dispatcher requires explicit manual run or enabled schedule; background flags alone do nothing. Idempotent claims, caps/spacing/window/suppression/recovery remain enforced.
4. Dashboard / Leads / Campaigns / Outreach / Schedules / Reports / Settings; old redirects, manual scan/email wizards and live detail/timeline views.
5. Meaningful unit, PostgreSQL, frontend and responsive browser acceptance, image-only deployment with only necessary additive migration; no data reset.
6. One redesigned Homestay email/PDF to agrawaljoy1@gmail.com; verify SMTP/Sent, report full body and commercial details; stop for owner inspection. All global flags stay false, real prospect scanning/sending paused, no 50-lead run.

No subagents requested. Work continues in current checkout. Earlier clean-start backup and send records remain immutable history.

Progress: deterministic content/8-page PDF, manual runs/items, schedules/dispatcher and simplified frontend implemented locally. 297 backend unit tests and 41 frontend unit tests passed; five focused browser checks passed. Final additive-migration PostgreSQL acceptance and final release images are in progress. Nothing from this redesign has been migrated/deployed/sent to production yet.

PostgreSQL acceptance: five unchanged integration tests passed; explicit reviewed-run queue duplicate test passed separately; schema-10 schedule dispatcher/duplicate claim test passed separately. The isolated dispatcher rerun passed after avoiding simultaneous global migration-lock acquisition. No production public data changed during these tests.
