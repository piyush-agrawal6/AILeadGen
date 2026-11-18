# Combined onboarding production release — 18 November 2026

| Requested result | Actual result and evidence |
|---|---|
| Why the UI disappeared | Astra deployed launch-branch sourcee02af6c, which lacked the Antigravity commits after the sharedb368971 base. Vercel built that selected snapshot with the correctdashboard root. No evidence of a stale build cache or wrong project root. |
| Restored UI source | Antigravity1a1b0b6 andc54a670: onboarding-ai.tsx/css, scoped onboarding shell rules in globals.css, guarded matchMedia in the existing auth background. Restored1560px shell, horizontal five-step navigation, gradient/dot mesh, structured company/offering/positioning/market cards, sticky Copilot and mobile drawer. |
| Preserved AI source | Allapp files are byte-for-byte unchanged fromcf0e436. Clean-schema routing/shared health, durable cooldowns, partial validated fields, same-object product evidence, exactly-five ICP enforcement, bounded provider jobs, safe diagnostics and contextual Copilot remain deployed. No legacyacquisition_preferences dependency was reintroduced. |
| Conflicts resolved | ai_router.py retains the verified Astra implementation. onboarding-ai.tsx uses Antigravity's layout with Astra's error diagnostics, actual retry controls, bounded React Query guidance polling, follow-up context and existing secure SubscriptionPayment. Feature-branch relaxed AI validation/defaults and unrelated legal changes were excluded deliberately. |
| Real website analysis | Actual Vertex/Cloud Run executionleadengine-worker-6pskk reviewedhttps://planebyte.com and generated meaningful description, positioning, bothIntent Radar/Growth Intelligence and audiences. |
| Five ICPs and persistence | Exactly five distinct hypotheses generated and explicitly saved in the isolated acceptance schema; reviewed profile edits persisted and saved context refreshed. No customer approval or profile overwrite was performed silently. |
| Copilot and UI contracts | Actual provider-backed contextual guidance passed. Frontend transport replay of those recorded real results passed structured cards, source evidence, manual edits, five-profile approval, guidance and research→mandatory payment. Failure/retry, draft retention, read-only members and mobile modal controls passed. |
| Auth/payments/data | Auth, API and worker runtime settings unchanged. Existing work-email/Google/native-account and Creem regressions passed. Signup/login200, guest onboarding307, unauthenticated private APIs401, unsigned Creem callback400. Creem Live and mandatory payment remain enabled. One customer account/session and original jobREADY preserved; no reset, real charge, subscription mutation or archive access. |
| Production frontend | Source0ad3295c87eba1f30a048e63cb4baef4e516c767, deploymentdpl_5aKuqqCJ5XR9Nw12K1wjSjTY2ypM, Git frontend tree3b991f594a7b54ec4a3b2e8d0c2dc9c6d768047f. Actual production alias and public/release.json independently match. |
| API / worker | APIleadengine-api-00183-led,100% traffic; worker generation79, imageworker:intent-only-cf0e43662f. No API/worker redeployment was necessary. |

## Tests and verification limits

- Final frontend:202passes in52files; types and focused lint clean. Production Webpack build and both actual Vercel candidate builds passed.
- Focused unchanged-backend auth/Creem/AI regression:86passes. Production source/manifest guard:4passes. Do not add overlapping focused UI counts as unique tests.
- Real provider pipeline: four actual successful Vertex requests in a guarded isolated clean schema on the current database, using the deployed worker identity/source. No customer setup allowance was raised or reset.
- Uploaded candidate source hashes independently matched onboarding UI/CSS, globals, billing, auth and approved policy files. Production/release.json and Vercel alias/source metadata prove the promoted revision. The public signup page preloads global shell CSS but not route-specific Copilot CSS; its asset scan is not misrepresented as a rendered onboarding visual test.
- No Chrome/browser automation or real payment was initiated. Signed-in visual and real-payment acceptance remain the owner's manual check. The new component/layout is deployed and its data/interaction contracts are tested; no screenshot-based visual certification is claimed.

## Ongoing release protection

`codex/production-integration-20261117` is the authoritative shared release branch. Both histories are retained by mergec08f72e. Recovery refs preserve each prior head; private archives and digests preserve the other worktrees'145/57 untracked files without modifying them.

Use the [integration process](PLANEBYTE_PRODUCTION_INTEGRATION.md). Packaging requires both UI/AI ancestry, current production ancestry and clean integrated worktrees. Vercel now requires `node scripts/verify-production-source.mjs --require && npm run build`; an old snapshot or unprepared Git preview cannot pass that build guard. No secrets, auth/billing environment or project root changed. The project's Git createDeployments setting reportsdisabled, but a same-commit queued Git preview was observed; that setting alone is not used as proof that previews cannot exist. Only the verified prepared candidate was manually promoted.

Public source identity: https://app.planebyte.com/release.json . Customer route: https://app.planebyte.com/onboarding . Private deployment/provider/test evidence: data/artifacts/verification/onboarding-ui-integration-20261117/combined-release-deployed.json and its neighboring restricted artifacts. Do not commit those private payloads or rerun historical reset operators.
