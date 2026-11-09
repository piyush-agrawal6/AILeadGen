# Acquisition and source-policy implementation

Status: deployed; final live acceptance remains pending. The automation upgrade is not marked complete.

## Current deployment

API `leadengine-api-00051-5b6` uses source-policy r13. The isolated acquisition worker uses r12; the repaired Maps/mail worker remains r9. Frontend `dpl_762jcLAVUWCVfqwHeFkpPksJgAre` is live at https://leads.planebyte.com. Schema13 was preserved without rerunning production migrations.

All four new source flags were enabled sequentially after controlled source acceptance. Existing owner-enabled automation flags and limits remain unchanged: 50/hour, 500/day, minimum1.2-minute spacing, daily targets500, follow-up3days, Asia/Kolkata. No provider credentials were added to the Maps/mail worker. It received only two source-dispatch capability flags and invocation permission scoped to the separate acquisition job.

## Implemented

- Central source policy: Overture discovery qualification; Firecrawl email-contactable discovery; CSV/XLSX/Sheets trusted qualified imports.
- New Overture scans require validated business email before deep analysis, then one meaningful selected opportunity. Balanced/Exploratory/Strict modes, bounded preliminary checks, late useful Lighthouse, negative email-search cache, freshness reuse, resource budgets and anomaly diagnostics apply only to new tagged scans.
- Firecrawl discovers official company websites and evidenced public email before analysis. No-email discoveries do not count, enter canonical qualified leads or consume deep analysis. Public contact provenance is retained through analysis. Checkpoint recovery completes pending analysis before treating the contactable target as complete; paid completed requests are reused.
- Trusted imports complete canonical intake before analysis. Missing websites, analytical scores and analysis failures cannot disqualify valid imported leads. OWNER_PROVIDED email provenance remains distinct from public evidence. Global suppression and content/PDF/send guards remain enforced.
- Run Emails supports inline CSV/XLSX upload -> mapping review -> qualified campaign -> actual email/PDF review through the existing outreach system. Upload never sends automatically.
- Schedules explicitly select Overture or Firecrawl. Reviewed intent, target, prompt and budgets persist; stale Maps coordinates cannot overwrite Firecrawl geography. Missing historical source remains Overture. Correct-source Run Now routing was observed; final automatic timer acceptance is pending below.
- Source-specific campaign funnels, separate CSV/Excel filters, email/resource counters and paginated qualification reasons are available.
- Acquisition progress reads use the existing authenticated per-user Redis cache for5seconds; active processing skips redundant campaign-audience calculation. Cache failure falls back to live reads. Safety and send decisions are never cached.

## Verified

| Controlled check | Result |
| --- | --- |
| Firecrawl Bristol | 5contactable qualified,5profiles/scores,5verified public contacts |
| Firecrawl recovery | No duplicate observations;0new paid requests during analysis resume |
| Google Sheets | 10valid rows ->10qualified imported |
| Excel ten rows | 10valid rows ->10qualified imported |
| CSV / smaller Excel | 3/3qualified each |
| Seattle bounded Overture | 12discovered ->3deep audits ->2qualified;0Lighthouse;128.53seconds |
| QA prospect messages/outreach | 0in the marked controlled source campaigns |
| Production CSV/Sheets AI mapping | Exact unusual-header mappings and validated repeat-cache hits; no import until approval |
| Progress cache live | 9.861s initial MISS;1.426s and1.360s repeat HITs, approximately86%faster |
| Linux exact-lock backend | 403passed,13skipped |
| Frontend | 43unit tests,23full browser checks,6latest source-browser checks; TypeScript/build passed |
| PostgreSQL | Original11cases covered across successful initial/focused/corrected runs; additional no-email LIKE regression passed |

Blank websites in the owner-controlled imported sample are recorded as analysis unavailable; no findings or scores were invented. No live prospect emails were authorized or sent by these QA flows. This phase does not claim a fresh tracking/reply/bounce acceptance beyond preserved infrastructure.

## Remaining before completion

1. Inspect production API-upload job `ee17549f-2db6-4f80-ac3d-c0699754d661` to confirm worker completion, expected single qualified row and no outreach/messages.
2. Inspect once-only automatic Firecrawl schedule `99a77399-f822-4b85-a6a0-55fc916c04e8`, due2026-11-02T14:41:20Z (20:11:20Asia/Kolkata). No Run Now was called. Verify exactly one dispatch, correct source, terminal result and no outreach. It has a one-lead/four-page bound and is not recurring.
3. Check controlled Run Now Firecrawl parent `18869f3c-c138-4087-b65b-c88f4507cb2c` after the scheduler capability repair. Correct-source child launch was observed; the parent had required review before the scheduler flags were repaired. Do not silently mark it complete.
4. Repeat final read-only health, feature flags, preserved limits and no-QA-email checks. Finalize evidence and readiness only after those results pass.

Automatic approval review could not execute the final production health read because its usage limit was reached. This is a review availability failure, not an unsafe-action determination. No bypass was attempted. The already-started cache measurement completed successfully. Resume production checks only when approval review is available again.

Evidence: `acquisition-phase1-acceptance.json`, `source-policy-controlled-acceptance.json`, `source-policy-seattle-acceptance.json`, `source-progress-cache-acceptance.json`, `source-api-upload-acceptance.json`, `source-auto-schedule-acceptance.json`, `source-schedule-acceptance.json`, and `source-scheduler-dispatch-config.json`.
