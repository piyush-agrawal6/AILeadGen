# Intent Radar Phase 2/3 final readiness

## Verdict — NO-GO for commercial production launch

2026-11-11. Substantial bounded functionality works, and confirmed defects were repaired with regression coverage. **Phases 2 and 3 are not fully complete.** Software gaps, independent AI-quality failure/coverage, commercial approvals and staging/customer acceptance remain. No commit/push/deployment or real email was performed.

## Reproducible requirement summary

Authoritative: `INTENT_RADAR_PHASE_2_3_REQUIREMENTS_AUDIT.md` / `.json`, generated review observations in `scripts/finalize_intent_radar_product_audit.py`, counts in `INTENT_RADAR_PHASE_2_3_AUDIT_COUNTS.json`.

| Status | Count |
|---|---:|
| Total individually assessed criteria | 510 |
| VERIFIED | 355 |
| IMPLEMENTED BUT NOT VERIFIED | 66 |
| PARTIALLY IMPLEMENTED | 50 |
| MISSING | 30 |
| BROKEN remaining after documented repairs | 0 |
| BLOCKED BY EXTERNAL APPROVAL | 4 |
| NOT APPLICABLE | 5 |

- Local implemented functional-contract coverage: **399/501 = 79.64%**. Excludes N/A and approval-only rows. Complete reviewed implementation gets one credit; partial/missing/unperformed larger independent-evaluation criteria get zero. Unverified implementation remains separately labeled.
- Independently checked requirement closure: **355/505 = 70.30%**. Only VERIFIED gets credit; excludes N/A only. Related tests/rendered pages cannot establish a complete broad customer workflow.
- These are equal-weight criterion counts, not feature-effort estimates, test rates or launch-readiness probabilities. Acceptance criteria and release gates are included as explicitly requested.

## Current verification baseline

| Check | Current result |
|---|---|
| Full backend | 822 passed, 57 explicitly skipped; seven warnings recorded |
| Isolated PostgreSQL 16 | 56 passed, disposable UTF-8 schemas, fresh/additive migration and security/recovery checks |
| Frontend unit tests | 143 passed |
| Supported Node runtime | v24.22.2 x64; archive SHA-256 verified |
| TypeScript | Passed |
| Isolated Next production build | Passed; separate product build directory/test configuration |
| Browser | 61 distinct scenarios passed; real-routing and UI-mocked evidence distinguished |
| Genuine source requests | HN Ask/Show/New/Top/Best/comments/jobs, Stack Exchange, W3C RSS, Discourse Meta; combined three-source discovery |
| Genuine Vertex | Existing gateway/model `gemini-3.6-flash`; draft and selected-ICP interpretation in browser accepted |
| AI smoke quality | **FAILED exact-category gate: 7/8** authored English cases; no high-intent false positives in this tiny set |
| Genuine Atom | Not accepted; parser implementation only verified with isolated synthetic Atom |
| Real Google/customer Gmail consent and live sending | Not performed; no real messages |
| Commercial/source-provider approval | Open |
| Staging/production acceptance | Open; no deployment |

Backend and PostgreSQL totals are not combined. Initial failures and final evidence are retained in `INTENT_RADAR_PHASE_2_3_COMPLETE_FUNCTIONAL_AUDIT.md` and `data/artifacts/verification/intent-radar23-product-*`.

## What genuinely works now

- Four-family authoritative catalog, honest approval/configuration state and SSRF-protected approved feeds; stale local Phase 1 process repaired without enabling sources.
- Reviewed bounded multi-source jobs, per-source progress/failure metadata, source-backed normalized signals, cancellation, persisted review/bookmarks/collections/opportunities and alerts.
- Revisioned opt-in monitor lifecycle, leases/fencing, durable dispatch and actual subprocess restart with completed-source checkpoint reuse; PostgreSQL replay accepted.
- Existing Vertex gateway, editable drafts, exact-source claim validation, selected ICP/revision checks, explainable heuristic scoring, bounded quotas and deterministic fallback.
- Real feedback persistence/reversal and refreshed analysis score; accurate seven-tool read-only MCP catalog and scoped tool access.
- Opportunity detail and monitor history/source labels repaired; source filter and bounded opportunity/alert pagination wired to APIs.
- Existing Lead Engine/Gmail B04 work preserved and applicable regression checks pass.

## Remaining local Phase 2/3 blockers — prioritize before launch

| Priority / criterion family | Required closure |
|---|---|
| P1 — P3.3 | Complete genuine bounded semantic retrieval/reranking, editable semantic exclusions and measurable keyword comparison; current candidate retention/on-demand analysis is partial |
| P1 — P3.7.01/.02/.04 | Implement dedicated grounded summary, buyer-problem and why-it-matters output/workflow; quotes alone are not complete summaries |
| P1 — P3.8 / P3.9.10 | Complete evidence-backed opportunity intelligence and actual feedback use in primary list-ranking/filtering |
| P1/P2 — P3.4/P3.5 | Full permitted profile/ICP criteria, versioned re-evaluation/customer comparisons, contradictory evidence and uncertainty/calibration acceptance |
| P2 — P3.10 | Agree and implement supported language detection/translation/language-aware search/cross-language behavior; original Unicode does not establish multilingual quality |
| P2 — P2.1–P2.7 | Complete supported incremental cursors, per-source accounting/retry policy, retention sweep and deployed bounded scheduling acceptance |
| P2 — P2.9 | Global monitor/saved collection paging/filtering, complete settings/default/control acceptance and high-volume result/pagination measurements |
| P2 — P3.11.21/.22 | Dedicated least-privilege source-health/workspace-context read tools where the original MCP contract requires them |
| P1 operational — P3.1/P2.10 | Actual existing-gateway token/currency usage plumbing, agreed cost ceiling, bounded latency/query/concurrency/alert-volume measurements |

The matrix records every partial/missing/unverified item individually. These are explicit Phase 2/3 blockers; they have not been disguised as credential errors, hidden controls or Phase 4 features. No new AI framework, paid infrastructure or expanded source permission was introduced.

## Owner-supplied configuration and external gates

See `PLANEBYTE_REQUIRED_CREDENTIALS_AND_LAUNCH_SETUP.md` and `PLANEBYTE_LAUNCH_SETUP_VARIABLES.md` / `.json`: **132 exact source-derived contracts, 50 explicitly present and 82 absent/defaulted** in inspected local files/process; values never recorded. Absent optional/default variables are not all missing credentials.

1. Review Stack Exchange/publisher/Discourse commercial terms, attribution, retention and polling; configure approved hosts and workspace feeds. Provide an eligible reachable Atom endpoint. HN jobs live acceptance is now closed, remains opt-in.
2. Approve scheduling/MCP/AI flags only with owner authorization, matching workspace grants and existing durable worker/client setup. Preview restrictions remain intact.
3. Supply approved customer integration encryption key/canonical Gmail callback through existing environment files or secret manager, complete owner OAuth/scopes/real mailbox lifecycle acceptance. Keep live sending separately gated.
4. Approve the preregistered independent AI protocol, representative licensed corpus, independent reviewers/adjudication and bounded spend. Current eight-case failure remains recorded; exact source quotes do not independently prove semantic correctness.
5. Verify attached production Vertex identity/IAM, model/cost policy, HTTPS/auth/signing/database/storage configuration, recoverable migrations and genuine staging/account workflows. Local ADC/model success is not production identity acceptance.
6. Perform owner-approved staging security/role/two-workspace/revocation/customer acceptance and bounded operational/recovery/capacity checks. No rollout should precede critical closure.

## Preservation and recovery

Starting 1,201-file checkpoint exactly matched prior source. Readback-checked SQLite preview backup retained source/customer history before local restarts. Final source checkpoint/changed-file manifest is recorded by the audit recovery procedure; generated Next files are separate from source changes. Existing versioned migrations 42/43 remain; this audit added no migration or data reset. Tracked generated Gmail whitespace findings were preserved rather than overwritten.

Final recovery target: `/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode/intent-radar-23-product-audit-closure-20261111/manifest.json`. Compare against the starting product-audit manifest; source/verification archives use SHA-256 and readback validation, including all-page screenshots and retained failed-browser traces. The previous final checkpoint is preserved. Evidence consistency validator: `scripts/validate_intent_radar_product_evidence.py`; machine-readable final test/count summary: `data/artifacts/verification/intent-radar23-product-evidence-summary.json`.

**Next action:** finish the named local Phase 2/3 blockers and independently verify them, then obtain source/quality/configuration approvals and execute staging acceptance. **Commercial launch remains NO-GO until those gates close.**
