# Intent Radar Phase 2/3 complete functional audit

2026-11-11. **Verdict: NO-GO for commercial launch.** This audit accounts for 510 detailed criteria; it does not declare Phases 2/3 fully complete. Remaining local gaps and exact acceptance blockers are individually recorded in the requirements matrix.

## Preservation and provenance

- HEAD `03398f62a3c040e2220157fd7726d7c1233c6969`, checked-out branch `main`. Original Lead Engine, Gmail B04 and Radar changes were already uncommitted and preserved. The agent made no branch change.
- Initial recovery readback matched **1,201 source files**, with zero source differences from the existing final Phase 2/3 checkpoint. The initial invocation failed because `/var` resolved to `/private/var`; explicit approved output succeeded, and the checkpoint script now normalizes the allowed base path.
- Starting checkpoint: `/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/intent-radar-23-product-audit-20261111/manifest.json`. Prior reports/evidence retained; current evidence uses additive `intent-radar23-product-*` artifacts.
- Existing preview was stale Phase 1 Python code, not a one-source registry in the current checkout. Signed preview inspection returned one source and 404s for Phase 2 config/health. After readback-checked SQLite backup and local API restart, it returns all four sources and HTTP 200 for config/health. Final inspection: `intent-radar23-product-runtime-healthy.log`. Existing local frontend was preserved.
- Preview backup/readback counts preserved four businesses, two Radar signals, two memberships and zero contacts/mail/suppression-send records. Backup integrity passed. No environment/OAuth/deployment settings, production records, production infrastructure, commits, pushes, deployments or real messages were changed/sent.

## Mandatory verification table

| Category | Result | Evidence | Remaining issue |
|---|---|---|---|
| Phase 2 source infrastructure | Functional bounded registry; partial full contract | Runtime healthy; connector/security tests; matrix P2.1 | Typed adapter contract, per-provider cursor/accounting/retry/retention details |
| Hacker News | Genuine Ask/Show/New/Top/Best/comments/jobs transport accepted | Product live-source log; providers tests | Recent bounded window; no historical search; automatic monitor cursor incomplete |
| Stack Exchange | Genuine official API accepted in isolated test scope | Product live-source log | Commercial approval; first bounded page; operator configured sites |
| Discourse | Genuine public Meta RSS accepted | Product live-source log | Instance-specific approval; feed-based category/tag limitations |
| RSS/Atom | Genuine W3C RSS; synthetic Atom parser coverage | Live-source log; connector tests | Genuine approved Atom endpoint not accepted |
| Multi-source discovery | Real three-source job/UI/persistence accepted | Product phase23/live browser; discovery tests | Sequential collection; full source paging/cross-family dedupe incomplete |
| Scheduled monitoring | Opt-in schedule/tick/pause; crash recovery repaired | Product recovery tests; PG recovery; phase23/live browser | Complete retry/backoff policy and deployed scheduler acceptance |
| Signal normalization/deduplication | Native IDs/URLs/evidence persist; idempotent | Backend/PG/browser | Cross-family identical-content policy incomplete |
| Phase 2 UI | Real routing/actions repaired and exercised | UI acceptance report | Global monitor/saved paging; full settings/filter acceptance |
| AI gateway | Genuine existing Vertex accepted | Live browser; live eight-case batch | Actual token/currency exposure and independent quality |
| AI classification | Functional; existing smoke quality gate FAILED 7/8 | Product live-AI log | Tutorial taxonomy disagreement; broader independent labels |
| Semantic matching | Partial candidates + explicit analysis | `classification.py`, `intelligence.py` | General semantic retrieval/reranking/exclusions/measurements missing |
| ICP integration | Real selected ICP/profile context and versions | Live browser; backend/PG tests | Full workspace criteria and different-ICP UI comparison unverified |
| Explainable scoring | Heuristic dimensions/unknowns/probability-null | Intelligence tests; browser | Calibration, full contradictions/urgency/switching factors |
| AI search assistance | Genuine editable proposal/refine/review/run | Live browser; draft fence tests | Full semantic/unsupported-filter proposal contract |
| AI summaries | Partial quote/interpretation interface | Active evidence/intelligence UI | Dedicated grounded summary/problem/why fields missing |
| Opportunity intelligence | Manual owned lifecycle/detail repaired | Product persistence browser | AI ranking and tailored recommendations incomplete |
| Feedback adaptation | Real reversible feedback affects displayed analysis/drafts | Product browser; intelligence tests | Primary signal/opportunity list ranking ignores feedback |
| Global/multilingual coverage | Original Unicode/declared feed language; unknown geography | Feed parser/provenance UI | Detection, translation, language-aware/cross-language acceptance missing |
| Phase 3 UI | Implemented controls work in tested flows | Product phase23/live/browser | Missing backend contracts remain customer-visible incomplete features |
| Integrations and MCP | Four providers; seven accurately described read tools | Runtime/UI; individual tools regression; developer browser | Dedicated Radar health/context tools and named-client launch acceptance |
| Tenant security | Isolated scope/fence tests pass | Backend closure; PG recovery; Radar/developer/browser | Full two-browser immediate-revocation journey remains unverified |
| Backend regression | **822 passed, 57 skipped** | `intent-radar23-product-backend-closure.xml` | Seven recorded warnings; legacy/live acceptance skipped by explicit gates |
| Frontend regression | **143 passed**; Node 24 TypeScript passed | Product unit log; types-closure log | UI tests do not substitute for live acceptance |
| Browser acceptance | **61 distinct passed scenarios** | Deduplicated current product browser JSONs | Some Lead Engine presentation tests mock APIs; isolated sessions are not genuine Google consent |
| PostgreSQL | **56 passed**, isolated disposable schemas | Product postgres-recovery XML | No staging/production migration acceptance performed |
| Node 24 build | **Passed, v24.22.2 x64** | Product build-routes log; types-closure | Build uses isolated output/test configuration, not production deployment |
| Live-provider verification | HN/SE/RSS/Discourse and Vertex accepted | Product live logs/browser | Not commercial activation or production acceptance |
| AI-quality evaluation | Eight authored cases **7/8**, no high-intent FP | Product live-AI log | Independent 120-case protocol/corpus/labels/cost gate open |
| Commercial approvals | BLOCKED | Source matrix/setup inventory | Owner/provider approval required |
| Staging acceptance | BLOCKED | Final readiness | No deployment or owner real-account acceptance |

Evidence root: `data/artifacts/verification/`. Backend and PostgreSQL are separate categories, not a misleading combined pass total. Browser identity is file plus full test title; repeated runs are not additional tests. The 61 distinct scenarios are 29 Lead Engine, 7 Radar, 4 product repair/all-page checks, 1 Phase 2/3, 1 genuine source/Vertex, 2 Gmail, 3 auth, 11 workspace, 1 Sheets integration and 2 developer/MCP.

## Confirmed defects and repairs

| Defect / root cause | Repair | Permanent evidence |
|---|---|---|
| Stale Phase 1 local API imported before Phase 2 code | Safe local restart after backup; preserve restrictions | Signed initial/healthy runtime logs; SQLite readback records |
| Completed source re-fetched after hard-kill | Store owned signal IDs/new counts/synthetic marker in source checkpoint; reuse only completed versioned records after current fences | Real subprocess kill/restart regression; PostgreSQL checkpoint replay |
| Draft cache write could use revoked context/changed ICP | Recheck/lock manager membership/product/selected ICP before shared-cache persistence | Draft revocation regression; existing cache/security suite |
| AI analysis could persist after monitor revision changed | Recheck owned monitor revision after inference | Concurrent-monitor-edit regression |
| Cache omitted Vertex project/location and actual instruction identity | Include project/location/prompt in input hash | Cache-identity regression |
| General alternatives/promotions/jobs/security/non-buying discussions scored like buying requests | Deterministic V3 request-context checks, negative penalties, no-intent ceiling 60 | Nine positive/negative classification regressions; live UI general-discussion evidence |
| Future timestamps received recency points | Require nonnegative age for both recency intervals | Adjacent scoring regression suite; independent calibration still open |
| Legacy source field mislabeled SE/feed jobs Hacker News | Return actual registry source name or Multiple sources | Multi-source/backend/live progression evidence; no provenance overwritten |
| MCP catalog claimed four tools while seven registered | Describe all seven real read tools | Product browser catalog; independent each-tool owned/foreign-ID test |
| Feedback score stayed stale in client response state | Prefer refreshed server history for same analysis timestamp | Browser save/reverse score assertions |
| Default ICP preference not applied to new discovery | Initialize criteria from persisted default ICP | Build/type and adjacent selected-ICP workflow; exact default-specific acceptance remains unverified |
| Monitor card hardcoded Hacker News/manual label | Render actual selected provider names and saved frequency | Multi-source monitor/history browser assertions |
| Monitor detail had no source-run history | Add owned latest-100 history panel | Product monitor history browser |
| Opportunity detail missing API/UI/Next allowlist wiring | Scoped GET, detail workspace and permitted UUID route | Real browser notes/save/refresh and foreign-ID regression |
| Opportunities/alerts inaccessible beyond fetched first page | Bounded page controls; describe current-page alert filters honestly | Type/build plus adjacent route workflows; high-volume pagination acceptance remains open |
| Signal source filter hardcoded Hacker News | Options from authoritative capability catalog | Four-family browser filter assertions |
| Alert threshold description promised suppression that backend did not perform | Describe threshold as high-relevance labeling, preserve all-match behavior | Source review; settings full acceptance remains open |
| Recovery checkpoint base path symlink mismatch | Resolve approved base consistently | Verified source checkpoint readback |

No migrations were added by this audit. Existing versioned migrations 42/43 and historical data remain intact. Missing substantive Phase 2/3 requirements were individually documented as local blockers rather than replaced by dummy behavior.

### Application/test source files changed by this audit

- Backend: `app/api/routes/intent_radar.py`; `app/intent_radar/{ai,classification,discovery,intelligence}.py`.
- Frontend routing: `dashboard/app/intent-radar/[[...segments]]/page.tsx`.
- Active frontend components: `dashboard/components/intent-radar/{advanced-controls,discovery,experience,integrations,monitor-experience,research-experience,settings-experience,signal-workspace}.tsx`.
- Permanent backend regression: `tests/unit/test_intent_radar_product_audit.py`; `tests/integration/test_intent_radar_postgres.py`.
- Browser regression/evidence: `dashboard/intent-radar23-e2e/{product,phase23,live}.spec.ts`; `dashboard/playwright.intent-radar-product.config.ts`.
- Recovery/live helpers: `scripts/checkpoint_intent_radar_23.py`; `scripts/verify_intent_radar_23_live.py`.
- New audit automation: `scripts/{audit_intent_radar_product,finalize_intent_radar_product_audit,inspect_intent_radar_product_runtime,inventory_planebyte_launch_setup,restart_intent_radar_local_preview,validate_intent_radar_product_evidence,verify_intent_radar_product}.py`.
- `.gitignore` adds only the new isolated product build directory. Next generated two new isolated-build type include entries in `dashboard/tsconfig.json`; existing entries/work were preserved. Generated `next-env.d.ts`/build artifacts are not business-logic edits.
- Required new audit/UI/readiness/setup reports, machine-readable matrices/counts and evaluation protocol were added. Prior Phase 2/3 checklist, implementation, verification, pending and source matrix reports received additive explicitly superseding notes. Lead Engine/Gmail source changes predating this audit were not attributed as new repairs.

Exact hashes and added/changed/deleted source paths are readback-recorded in the final product-audit recovery manifest, compared with the verified starting 1,201-file checkpoint. No source deletion or new migration was intended.

## Hardcoded/fake/disconnected inventory

- No production-path synthetic source or AI success implementation was found in the active Radar routing/backend. Synthetic transports remain in explicitly named isolated fixture/test servers. Auth fixture cookies are test-only.
- Confirmed disconnected/hardcoded items repaired: monitor provider/frequency label, HN-only signal filter, four-tool MCP description, default ICP, feedback score, opportunity detail and source-run history.
- Suggested search text is editable preset input, not discovered results. Heuristic scores/quotas are explicit bounded defaults, not calibrated outcomes or subscription billing.
- Legacy `pages.tsx`/`workspace-pages.tsx` Phase 1 components remain preserved; active catch-all routing uses `experience.tsx`. Their historical HN-only content does not define the repaired catalog.
- CRM/Sales/automation/external notifications and named ChatGPT/Claude clients are labeled Planned/manual/unverified. No fake OAuth, API key request or successful connection was introduced.

## Initial and subsequent failures, preserved

1. Initial backend: **9 failed, 799 passed, 56 skipped**. Audit-level `GEMINI_API_ENABLED=false` disabled synthetic Gemini tests prematurely. Corrected harness: all 35 acquisition-source tests passed. Final full suite passes above.
2. New regression setup: missing imported `owned` fixture caused two errors; corrected shared-fixture import. Initial each-tool test used wrong function/argument contract and wrong foreign actor; corrected tests to actual `read`/`id`/`search` and verified memberships.
3. New subprocess recovery setup initially assigned nonexistent `database_backend` settings property; removed test-only assignment. Next run exposed the **real completed-source refetch defect**, repaired and verified by hard-kill/restart and PostgreSQL.
4. First new browser run: one ambiguous locator and one genuine Next opportunity-route 404. Both corrected. Later test runs navigated before opportunity create/save completed, causing absent records/client disconnect; assertions now wait for actual persisted API values before reload. Final persistence run passes; failed traces/logs retained.
5. Platform wrapper initially selected auth-only tests despite its broad name. Separate actual workspace/integrations/developer runs now recorded and deduplicated.
6. PostgreSQL startup inspection initially tried nonexistent local roles `planebyte`/`postgres`; the preexisting disposable cluster role `radar_test` is used. PostgreSQL acceptance passes without production access.
7. Node arm64 archive was initially downloaded on this x64 host; x64 v24.22.2 checksum was verified and that binary was used. Node 26 is not the supported baseline.
8. Immediate post-restart runtime probe raced startup and returned connection refused; subsequent bounded healthy inspection passes. Restart helper now waits for health.
9. **Live AI quality remains failed**: 7/8 exact categories. This failure was not suppressed, relabeled or retested until a convenient pass.

## Remaining engineering and acceptance blockers

The matrix enumerates **50 partial, 30 missing and 66 unverified criteria**, including semantic retrieval/exclusions/ranking, structured summaries, complete feedback list-ranking, multilingual processing, full ICP factors, source cursor/retry/retention completeness, global saved/monitor pagination, actual AI usage/cost metrics and measured high-volume/latency acceptance. Four approval rows remain externally blocked. These are Phase 2/3 blockers, not Phase 4 work or requests for new infrastructure.

Credentials alone cannot close these software and quality gaps. Exact presence/source/owner instructions: `PLANEBYTE_REQUIRED_CREDENTIALS_AND_LAUNCH_SETUP.md` and its full 132-variable annex. Independent protocol: `INTENT_RADAR_AI_INDEPENDENT_EVALUATION_PROTOCOL.md`.

## Quantitative rules and result

`INTENT_RADAR_PHASE_2_3_REQUIREMENTS_AUDIT.json` is the machine-readable row source; `scripts/finalize_intent_radar_product_audit.py` and `INTENT_RADAR_PHASE_2_3_AUDIT_COUNTS.json` reproduce results. Counts: **510 total; 355 VERIFIED; 66 IMPLEMENTED BUT NOT VERIFIED; 50 PARTIALLY IMPLEMENTED; 30 MISSING; 0 BROKEN remaining after documented repairs; 4 BLOCKED BY EXTERNAL APPROVAL; 5 NOT APPLICABLE.**

- Locally implemented functional-contract coverage: **399 / 501 = 79.64%**. Denominator excludes only N/A and external-approval rows. Numerator requires explicitly reviewed complete local implementation; partial/missing and unperformed independent-evaluation rows get no credit.
- Independently checked requirement closure: **355 / 505 = 70.30%**. N/A excluded; external/unverified/partial/missing remain in denominator. Exact bounded behavior matters; a related suite alone cannot close a full customer workflow.
- Neither percentage is a test-pass rate, weighted product effort estimate, production readiness score or claim that all visible controls are accepted. The source audit retains individually incomplete requirements even while regression suites pass.

**Commercial production verdict: NO-GO.** Finish named Phase 2/3 engineering blockers, independent AI evaluation, provider approvals and genuine staging/customer acceptance before release.
