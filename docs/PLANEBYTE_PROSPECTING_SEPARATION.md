# PlaneByte Lead Engine — prospecting separation

Status: implemented locally; controlled local acceptance passed. This is not a production deployment or public SaaS readiness certificate.

## Current product flow

```text
Overture / Maps                    AI + Firecrawl             CSV / XLSX / Sheets
Business / industry validation    Published website + email   Reviewed owner mapping
              \                         |                         /
                 Normalize, deduplicate, verify workspace
                                  |
                 Bounded public company information
                                  |
                 Company / ICP fit and campaign membership
                                  |
                 Master Leads, contacts and manual routing
                                  |
                 Owned email template, exact message preview
                                  |
                 Existing guarded outreach and reply tracking
```

Company qualification is distinct from contact availability and sending permission. A fitting Maps company can remain qualified without a website/email and be available for manual contact. Firecrawl retains its explicit contactable-source target: results without a website and publicly supported email are excluded before company crawling. Trusted imported businesses remain qualified when company enrichment is partial, missing or fails. No source requires a poor website/SEO/security score.

## Execution boundary

`app/prospecting/policy.py` applies `PROSPECTING_V1` to current execution, including resumed runs with historical assessment flags. It disables website assessment, SEO/AEO/GEO, Lighthouse, security/VAPT and PDF flags, and zeros assessment budgets. Saved historical configuration is not permission to run old work.

`app/pipeline/runner.py` no longer imports or calls the audit, opportunity-score, Lighthouse, screenshot, report or social deep-analysis engines. It preserves source discovery, deduplication, industry validation, chain policy, owned canonical observation, progress, cancellation, runtime limits, leases, exports and recovery. Companies are committed progressively as bounded enrichment groups complete. Unprocessed discovery candidates are not pre-marked qualified.

`app/prospecting/intake.py` uses the existing SSRF-safe crawler: at most three relevant public pages per company, two companies concurrently, bounded request/content/runtime budgets, robots policy, same-domain redirect checks and public contact extraction. It does not probe sitemap/performance/security endpoints. It retains source excerpts, URLs and retrieval timestamps; excerpt summaries are labeled `SOURCE_EXCERPT`, not falsely represented as AI-generated/verified business facts. Existing reviewed company-profile/ICP AI services and the shared Vertex gateway remain separate and unchanged.

Fresh company information can be reused for seven days only for the same canonical company, exact website and verified workspace. Contact evidence and historical qualification metadata remain distinguishable. ICP ownership is checked before crawling; unsupported/unmeasured criteria stay unknown. A run that exhausts its bounded candidate pool records a target shortfall rather than manufacturing results.

## Outreach and schedules

Campaign outreach requires an explicitly selected, enabled workspace-owned template. No experiment strategy, audit finding, AI-copy call, report or static capabilities PDF is substituted. Current campaign eligibility includes previously excluded companies with no assessment findings. Preparation produces the exact tracked preview through the existing mail service; the owner still reviews and starts sending.

Sender/session integration, SMTP/IMAP, tracking, reply matching, rate/spacing/windows, permanent contacted history, unsubscribe, DNC, hard-bounce and duplicate-send protections are retained. Company qualification does not override any of those protections.

Discovery schedules retain Overture and Firecrawl source selection, timing and rotation. Their effective execution uses the prospecting boundary. Historical experiment schedules are skipped by the dispatcher; the experiment tick does no database/provider work. Direct experiment preparation and source-start entry points reject new execution even if internal archive reading is enabled. A completed legacy combined discovery with no owned template is held for review instead of substituting audit copy or repeating acquisition.

Report dispatch is rejected before cloud credentials/network access. Report jobs no longer consume Lead Engine dispatch capacity; the report worker entry point exits without rendering. Historical queued/report records are not deleted or automatically regenerated. The CLI report command is blocked, and browser/Lighthouse/PDF prerequisites are removed from current worker health/canary checks.

## UI and API changes

- Find Leads and schedule editors use company targeting, optional owned ICPs, source selection and bounded resource controls. Opportunity categories, score thresholds and audit budgets are removed from the current UI.
- Send Emails selects a campaign/import and a real workspace template. Preview/edit and the existing review/start controls remain.
- Company pages show company evidence, public contacts, ICP match and collaboration history. Existing assessment findings are collapsed historical records, not the primary product experience.
- Current lead tables omit assessment scores, opportunity filters and audit columns. Navigation does not advertise assessment/experiment products.
- `/scans`, `/scans/new` and numeric `/scans/{id}` browser URLs are compatibility redirects to campaigns, Find Leads and `/discovery/{id}`. Discovery progress shows current company intake rather than an audit pipeline.
- Historical documents remain downloadable with ownership checks; generation/regeneration controls are removed. Unregistered loose numeric HTML filenames are not served as ownership evidence. Files remain on disk for controlled reconciliation.
- `POST /api/leads/{id}/report` and `POST /api/leads/{id}/pdf-reports` return 409 without generating anything. Historical typed report GET/download routes remain scoped and read-only.
- Internal archive writes return 409 even when archive reads are permitted. Default disabled-archive access remains 404; owner/internal workspace checks remain enforced.
- Current campaign funnels use company-information/contact/qualification metrics. Original assessment metrics remain separately identified as `historical_assessment_metrics`; legacy source-count keys are retained for compatibility, with current UI labels describing company information.
- Deprecated request fields remain accepted for compatibility but cannot activate assessments. Existing historical score/detail fields and filters are read-only compatibility contracts, not current qualification gates. No database columns or migrations were dropped.

The audit also found legacy company search/detail routes omitting their available workspace arguments. They now pass verified workspace membership into the repository. Artifact download checks ownership before storage access; a foreign or absent context cannot fetch a file. Tests cover these denials without relaxing the old workflow access tests.

## Preserved Search Visibility and historical code

`app/search_visibility/structured_data.py` now owns the reusable saved-HTML structured-data parser. `app/audit/structured_data.py` is an import compatibility shim. `app/search_visibility/report_quality.py` owns historical assessment/PDF validation, loaded lazily by compatibility callers. Current mail quality checks depend on workspace templates, not report content.

Existing static SEO/opportunity parsers, assessment snapshots, PDF renderers, experiment attribution/analytics and Lighthouse adapter are retained for historical support or future extraction. They are not imported/executed by the prospecting runner. The module registry marks Search Visibility **PLANNED** and Security Assessments **DISABLED**. No functioning Search Visibility/GEO product or authorized security assessment service is claimed by this change.

The repository audit found passive configuration observations and VAPT marketing copy, but no implemented Nmap/Nuclei/SQLMap/ZAP-style active vulnerability engine to remove. No third-party security testing was performed.

## Dependency and data audit

Dependency/import and execution-reference audits were recorded before removing runner branches and obsolete page code:

- `data/artifacts/verification/stage27/prospecting-dependency-audit.txt`
- `prospecting-dependency-manifests.txt`, `prospecting-runtime-final-audit.txt`, `prospecting-security-workflow-audit.txt` in the same directory.

No package was removed speculatively. BeautifulSoup/lxml/httpx remain required for safe public company crawling; DuckDB for Overture; openpyxl for imports/exports; Playwright for browser regression and retained adapters; ReportLab/pypdf for historical documents/optional attachment validation; root Lighthouse remains associated with the retained future-product adapter. Existing deployment images/manifests and production infrastructure were not modified by this cleanup.

No schema change was needed: schema 28 and every migration remain intact. No customer table, history, suppression record, campaign, report or operational database was reset, truncated or deleted. Fixture databases are isolated test artifacts. Preservation tests compare complete saved assessment rows, migration history and permanent contact-safety ledgers before/after enrichment.

Verified pre-change source checkpoint: `data/backups/pre-prospecting-separation-20261106T064750Z/source.zip`. Source checkpoint creation excludes environment files, databases and generated build output; it is not a production database backup or permission to perform cleanup.

## Verification

| Check | Actual result |
|---|---|
| Full backend, including real local PostgreSQL | 624 passed, 1 explicit live-mail skip; 22 PostgreSQL passes included |
| Frontend unit tests | 89 passed |
| TypeScript | Passed |
| Isolated production frontend build | Passed |
| Workflow browsers | 26 passed |
| Workspace/onboarding/ICP browsers | 10 passed |
| Authentication browsers | 3 passed |
| Real signed local gateway browser | 1 passed |
| Customer-connection browser | 1 passed |
| Data/history preservation and prospecting-specific tests | Passed; included in final backend run |

Machine-readable final results: `PLANEBYTE_PROSPECTING_ACCEPTANCE.json`. Logs are under `data/artifacts/verification/stage27/`. Initial separation failures and intervening failures are retained; they are not hidden or counted as passing acceptance.

All provider acquisition and real sending remained disabled during verification. Mail transport/DSN/reply tests use isolated fixtures; the explicit live-mail test is intentionally skipped. No deployment, OAuth/secret changes, production scan, real email or security test was performed. Public signup and the broader SaaS production release remain blocked by the existing release checklist, including approved staging and exact locked-runtime validation.
