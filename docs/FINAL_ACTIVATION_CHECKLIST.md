# Owner review gate — manual-first release

Production activation is NOT performed. The earlier global daily-acquisition activation procedure is superseded by the manual-first workflow.

- [x] Existing data preserved by the single required additive schema-10 migration.
- [x] API/worker and simplified frontend deployed; production read-only smoke passed.
- [x] All three environment flags remain false; acquisition/outreach database controls and Scheduler jobs remain paused.
- [x] Inbox/reply sync restored to its existing five-minute schedule.
- [x] Four evidence-led email variants, current PDF format and first-contact quality gates are available.
- [x] Exactly one redesigned Homestay example sent only to agrawaljoy1@gmail.com using the controlled redirect.
- [ ] Owner inspects the actual email and eight-page PDF and approves the client-facing format.
- [ ] Owner reviews the new frontend and approves infrastructure sending capability separately from any run.
- [ ] Owner manually creates the first intended qualified-lead scan from Find Leads. No 50-lead run has been started by the agent.
- [ ] Owner reviews qualified leads, exact email previews/PDFs, recipient selection, limits and window before starting an email run.
- [ ] Any recurring work is created and explicitly enabled in Schedules. Flags alone never constitute a schedule.

Do not resume the old acquisition/outreach jobs merely to start unrestricted daily work. Database schedules and explicit manual runs are now the execution authority. Cloud Run/Secret Manager capability changes are infrastructure administration, separate from normal daily dashboard use. Do not enable flags or a real outreach run until the owner approves.
