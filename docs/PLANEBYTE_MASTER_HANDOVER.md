# PlaneByte master handover

> **Current checkpoint — 17 November 2026:** Creem-only Live checkout is enabled on API `leadengine-api-00178-juv` and frontend `dpl_Bnw3PDBXntW1sAEyCbirdHbqK7NU`. The owner-approved exact test-account reset deleted21rows; zero customer accounts/workspaces remain. Backup/exact restore and post-reset checks passed. Fresh controlled signup for contact@planebyte.com: https://app.planebyte.com/signup . Mandatory Step5 and72-hour card trial are deployed; the owner performs the real signup/payment test. [Exact current result](PLANEBYTE_TEST_CUSTOMER_RESET_20261117.md). Older account, trial, checkout-disabled and revision statements below are historical. Do not repeat the reset.

> **Current P0 — 17 November 2026: clean Neon migration completed.** See [clean database release](PLANEBYTE_CLEAN_NEON_MIGRATION_20261117.md). Production API `leadengine-api-00168-his` (100%) and both database-using workers run source `b2e27ac`, use the new pinned database secret and schema profile1004. Zero customer accounts/users/workspaces/sessions/trials were verified at04:57UTC; no historical customer data was copied. Old Neon schema51/201tables and checked customer/financial/security records remain unchanged. All old revision tags were removed. Five schedulers and API database polling are off; bounded request-driven mail/AI remain configured. Final backend1,197pass/one real-outreach skip; actual clean-schema Vertex website/five-ICP workers and actual Cloud Run write/read/rollback pass. **Fresh contact@planebyte.com signup is ready for the owner's production test**; OTP and the full new-database customer journey remain pending that test. Public registration and checkout stay closed. Older reset/schema51/revision161 statements below are historical. The operator root `.env` DATABASE_URL remains the archive: use DATABASE_URL_NEW explicitly for current product operations, never default mutation scripts on the archive.

> **Latest P0 checkpoint supersedes the historical status below.** See [reset and authentication execution](PLANEBYTE_P0_RESET_EXECUTION_20261116.md). Reset complete:747rows deleted after exact201-table backup/restore/dry run; protected financial/security/system records preserved. Do not repeat it. Legal version planebyte-2026-11-16-v1 is published. Real work-email OTP delivery/verification, exact7-day trial, website research, reviewed profile/3ICPs, setup AI assistant and completion passed on production. The initial3-versus5 count and dashboard pool timeout were repaired in sourceb71e1c3, now API161100% with matching workers; frontendf4f1708 remains live. Final backend1,173passes/one explicit live-mail skip; onboarding browser2passes; actual isolated Vertex returned5distinct segments. Browser control was stopped before the final signed-in dashboard recheck; owner deferred password login/recovery. Fresh production exact-five acceptance remains unverified; do not reset the trial or raise caps. Public signup and checkout stay closed. Old Gmail admission, legal approval, flag-off, rollback149 and reset-authorization statements below are historical. Preserve Lead Engine source. No hosting-plan decision is pending; the owner handles it separately.

Updated 16 November 2026. Completed, verified non-payment improvements are deployed. **Full public paid launch is NOT READY.** Public signup and checkout remain closed. Read the current evidence below; historical pre-repair documents are retained in `archive/20261116-before-ai-repair/` and must not be used as current status.

## Final production result

| Component | Verified current checkpoint |
|---|---|
| Repository | `/Users/planebyte/.codex/worktrees/planebyte-public-launch/planebyte-leadgen`, branch `codex/public-launch-20261115` |
| Backend source | `dbfe6a6148a3c057770b69fb4971c28a6fd3d519` |
| API | `leadengine-api-00151-tij`, 100% customer traffic; https://leadengine-api-befca7xg4a-el.a.run.app |
| Workers | All three existing jobs use `worker:intent-only-dbfe6a6148` |
| Build | `b164ea2e-ae0f-4b5f-8549-54acd4758822`, SUCCESS |
| Frontend source | `64e9f0bada442c1e2c3bf2c7178601ffccc0c1cc` |
| SaaS | https://app.planebyte.com → READY `dpl_8wWL8WssS7nfp9s2VcuS1t56DXE6`, `leadengine-r5ykoikx4-piyushagrawal6s-projects.vercel.app` |
| Database | Schema **51**, migrated additively from46; five migrations, second0, no row loss |
| Email/diagnostics | Transactional Resend and safe setup attempt history enabled and genuinely verified |
| Admission/payments | Native accounts/trial/public signup, unverified checkout and unrelated outbound sending remain disabled |
| Rollback | Schema51-compatible flag-off API149, with explicit future native-enforcement caveat below |

Detailed ten-part outcome and exact proof: [Launch verification](PLANEBYTE_LAUNCH_VERIFICATION_20261116.md). Feature/route status: [Complete checklist](PLANEBYTE_COMPLETE_LAUNCH_CHECKLIST.md). Next work: [Next agent](PLANEBYTE_NEXT_AGENT_START_HERE.md).

## Completed repairs and actual acceptance

- Grounded company paraphrases use independent evidence review; atomic facts/quotes remain exact. Meaningful previews, metadata/JSON-LD, business-page prioritization and safe bounded crawling are implemented.
- Consistent3–5 ICP support, distinct targeting validation, exact service references and reviewed persistence are implemented. Suggestions remain hypotheses, not verified customers.
- Compact onboarding guidance understands saved context, unsaved draft and private follow-up history. It does not silently save, send or substitute static documentation as an AI answer.
- Schema51 retains safe attempt/stage/error/provider/duration events. Actual production job `78c8de87-fe36-477a-a44d-fca4b316a6a6` passed with four events and Vertex identity. Historical missing errors were not fabricated.
- Canonical company/offering context reaches research/global assistant. Lexical fallbacks cannot be cached and relabelled as validated AI.
- Report schema/prompt requires one citation per distinct discussion in each item. A measured3,000-token response exhausted its budget on thinking; the repaired bounded7,000-token contract passed a genuine Vertex request with4themes,8findings and20 exact citations. Production report acceptance is deferred by the ordinary daily operator cap, not represented as passed.
- Auth styling is preserved; the mobile theme button is no longer clipped and the unverified “Inc.” suffix is removed.

An authorized clean owner workspace completed real website→reviewed profile→five distinct ICPs→approval→saved defaults→contextual assistant/follow-up→completion. The full flow ran on125497a with unchanged setup modules in finaldbfe; final-source and schema51 workers were separately verified. Original owner/SyntaxWars profiles were not overwritten. No product grant, monitor, search or outreach was started by setup.

Controlled real OTP/recovery/password-change emails to `contact@planebyte.com` passed normal isolated account services, verification, trial, reset and revocation. Production independently passed actual encrypted outbox→Cloud Run worker→Resend→provider-signed callback→DELIVERED. Its exact test invitation was revoked; no membership was granted. No production customer password was changed. Delivery is provider-confirmed; mailbox contents were not independently retrieved.

## Verification boundaries

- Backend:1,153 passed, one explicit live-mail skip, eight warnings; PostgreSQL and isolated real Chromium included.
- Frontend:181 passed, types/focused lint/fresh build pass; final authentication account browser passes.
- Local product10/onboarding2/accounts1 browser tests pass with synthetic external transports, clearly separate from real-provider acceptance.
- Deployed guest browser:12 light/dark screenshots at1440/390/320, visible theme controls, theme persistence, closed signup and genuine Google canonical S256-PKCE handoff pass. A fresh completed authenticated callback is still unverified. Auth.js retains its default PKCE configuration; no new OAuth credential/config change was made.
- Final API/three worker images, traffic, safety flags and Resend bindings verified. Bounded API151 ERROR-or-higher count0; no uptime/scale/SLA claim.
- Fresh production MCP with official SDK2.3.0 passed HTTPS/tool discovery,13 read tools, authorized read, unknown-resource denial, hidden Lead tools absent and revoked-key401. Named GUI clients and customer integrations remain separate; cards do not certify working adapters.

Evidence is restricted under `data/artifacts/verification/onboarding-repair-20261116/`. Do not overwrite `public-launch/final/` or commit private provider/customer results. Backend source and frontend source differ intentionally; subsequent documentation commits do not change deployed code.

## Data, architecture and rollback

Preserve the FastAPI/Next16 modular monolith, PostgreSQL, existing Vertex router, real Google auth, workspace/session/integration services and all Lead Engine functionality/data. Lead Engine remains unavailable to customer Radar routes/workers. Owner branding/dashboard/Settings/Graph/Discover/theme changes are preserved. The other owner checkout remains at15d40b8 with unrelated untracked work; never reset or stage it.

Fresh snapshot: `data/backups/beta-recovery-20261116T071702Z/production.dump`,118,860,123 bytes, SHA256 `31bd74ca2c8626755ea98855ce0e242ca0087416ecbda84054f68f09ce053b13`. Exact isolated restore,46→51 and idempotency passed without original data-table changes. Production migration found no row loss; only migration history and routine health/retention cursors changed among original tables. No reset, truncation, cleanup or purge occurred.

Current source and runtime snapshots are under `data/backups/product-dbfe6a6148/` plus mail runtime snapshots in the new verification directory. API149 is a tested schema51-compatible flag-off rollback through the `schema51-rollback` tag; customer traffic remains on151. Restore only the intended image/config/traffic references and recheck scoped reads. Never restore a stale database snapshot to undo application changes, and never cold-start old65e9 against51.

**After native enrollment, rollback must retain access-period enforcement.** API149's flag-off configuration is only appropriate while no native managed workspace exists. Schema checks intentionally refuse enforcement-disabled rollback once managed customer rows exist.

Frontend prior `dpl_8qft5cRk9oGjRJRkCz6uh1fX9Xsa` remains available but contains the old header/footer defects. Prefer corrective release unless rollback is necessary. Netlify marketing was not redeployed; no unrelated infrastructure, OAuth credentials or `.env` file was modified.

## Approved owner policy and exact remaining blockers

- Trial:7days, no card/automatic renewal;5searches,3shared AI operations,150k reserved tokens,1manual monitor/member; once/person/domain. Paid schedules/reports/API/MCP. Native ledger remains off live.
- Monthly:USD59/149/379/custom, exactly30days, manual renewal/plan changes queued after existing terms, no early upgrade/proration/unused-time credits or recurring mandates. Annual calendar-year model exists; annual prices/cadence unapproved, checkout off.
- No GSTIN currently; do not invent/collect GST or require GSTIN. PayU account-specific USD charging must be verified.
- Initial-purchase refund request within7days, mandatory rights preserved; ordinary verified-closure deletion within30days, backups target≤90days, justified exceptions. No automatic real refund or purge is authorized.

**OWNER APPROVAL REQUIRED — verified legal fact:** legal contracting name/legal form/official address. Complete four legal drafts remain unpublished; do not ask again for approved refund/retention decisions.

Owner is personally checking PayU USD/international/settlement permissions. Separate valid Test Mode credentials/capabilities and actual KYC record remain missing; existing live key/salt are present and must not be requested again. No real payment/refund/mandate is authorized.

Vercel Hobby was reverified; owner explicitly authorized continuing current development/deployment and will review commercial hosting before paid launch. Do not upgrade automatically or block unrelated work.

Technical acceptance still needed: fresh completed Google/native customer journey after legal/admission gates; report/global semantic acceptance after daily operator capacity resets (95,884/100,000 reserved;4,116 left); hardened Cloud Run JS-only rendering acceptance before enabling its currently-false flag; permitted source/customer integration/independent quality work. Private-read latency remains roughly3–7seconds in a small sample, with cross-region database round trips; performance/scale targets are not certified.

Resend key is no longer a blocker. Existing key and webhook secret version1 are bound and verified. Hostinger SMTP/IMAP remains unverified; do not change legacy credentials or infer working customer mailbox integrations.
