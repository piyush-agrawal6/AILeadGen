# Intent Radar Phase 2/3 UI acceptance

2026-11-11, actual Next.js routing/signed gateway, isolated owned databases, supported **Node 24.22.2** production build. **Partial product acceptance; NO-GO for launch.** A page screenshot does not establish every action or external integration.

## Evidence classification

- Radar integrated tests use real APIs, authorization, jobs and persistence. Network/AI transports in named fixture servers are explicitly synthetic.
- `intent-radar23-e2e/live.spec.ts` uses genuine HN/Stack Exchange/W3C feeds and configured Vertex. It asserts `synthetic=false`, real provider/model and selected ICP, with no contact/mail writes.
- Auth.js fixture session cookies exercise actual session/routing policy but do not establish completed real Google consent. Auth handoff is separately tested.
- Some existing Lead Engine presentation tests intercept synthetic API responses; their passes count as presentation regression, not live/integrated customer acceptance.
- No provider was activated in the owner's workspace. Final preview states: HN Available; Stack Exchange Requires approval; RSS/Discourse Not configured; schedules opted out.

## Page/action matrix

Screenshots are under `data/artifacts/verification/intent-radar23-product-product-pages/`; each listed index has `page-{index}-1440.png` and `page-{index}-390.png`. All screenshots wait for real page data/skeleton completion and verify no 404/viewport overflow.

| Page / screenshot index | Actual acceptance performed | Remaining limitation |
|---|---|---|
| Overview / 0 | Product switch, real overview route/metrics, navigation, screenshots | Not every dashboard card/link independently clicked |
| Discover Intent / 1 | Natural-language proposal, edit/refine, reviewed multi-source search, progress/cancel, real live-source job | Semantic retrieval/negative context/paging incomplete |
| Monitors / 2 | Create/edit/duplicate/archive/restore/pause/resume/manual checks persist | First 100 list only; global filtering/paging incomplete |
| Create Monitor wizard / 3 | Multi-step validation/review; inert creation; explicit schedule frequency; no automatic run on save | All invalid-input/mobile keyboard combinations not exhaustive |
| Monitor detail/edit / 4 | Real providers/frequency; owned run history; edit revisions; next/last run; controllable-clock pause/resume | Latest 100 source-run entries, no paged full history UI |
| Intent Signals / 5 | Search/review/saved/bulk workflows; four-family authoritative source options; list route and screenshot | Full high-volume/filter/sort combinations unverified |
| Signal detail / 6 | Original URL/evidence, status/notes/save/opportunity, grounded on-demand AI, selected ICP and reversible feedback score | Full structured source summary/why/problem payload missing |
| Saved Signals/collections / 7 | Bookmark/collection/notes/tags persist and refresh; empty-state isolation | First 100 records locally filtered; no global collection search |
| Opportunities / 8 | Status/priority/notes/next action and real detail links; persisted updates | AI ranking absent; high-volume paging acceptance open |
| Opportunity detail / 9 | Scoped GET + Next allowlist + form + source evidence; save/API-readback/reload accepted | Tailored AI research suggestions and distinct research state incomplete |
| Alerts / 10 | New-match alerts, read/unread persist, shared notification reflection, page controls | Inbox tabs filter current page; external delivery Planned |
| Integrations & MCP / 11 | All four families discoverable with truthful restrictions; config/health endpoints; seven read-tool modal | Named client connection/approval not inferred; dedicated health MCP tool missing |
| Radar settings / 12 | Real scoped settings route; default ICP wiring inspected; honest threshold description | Every setting/default propagation not independently accepted |
| Shared navigation/product switching | Real desktop/mobile/keyboard product switching; no cache leakage after workspace change | Genuine customer Google sign-in completion still external |

Additional evidence:

- `intent-radar23-product-product-pages/evidence-opportunity-{1440,390,320}.png`: populated opportunity, source title/rationale and saved notes.
- `intent-radar23-product-product-pages/evidence-mcp.png`: actual seven-tool contract modal and disabled/unverified connection state.
- `intent-radar23-product-phase23-recovery/evidence-{1440,1280,768,390,320}.png`: grounded fixture workflow.
- `intent-radar23-product-live-final/evidence-{1440,1280,768,390,320}.png`: genuine public-source detail. Source retained; unrelated discussion shows **General discussion, 60/100**, not a buying-probability claim.

## Journey outcomes

**A — workspace/source/search/save/opportunity/monitor/schedule/alert:** integrated fixture and separate real-source journey pass actual routing/persistence. Profile/ICP CRUD and onboarding pass shared workspace suite. Genuine new-customer Google consent and deployed recurring dispatch remain external acceptance.

**B — AI research:** real editable Vertex proposal and real selected-ICP analysis pass; feedback save/reverse changes displayed server score. Complete summaries, semantic discovery and feedback-based primary opportunity ranking do not exist as full workflows; Journey B is therefore partial despite passing its implemented-path tests.

**C — security:** real workspace switch/direct ID denial and isolated backend/MCP revocation checks pass. Complete two-browser immediate membership-revocation acceptance remains unverified; no client resource ID grants membership.

**D — shared SaaS:** Lead Engine dashboard/company/contact/ICP/list/task/no-email workflows and preserved Gmail B04 synthetic lifecycle/review/send safeguards pass. Genuine mailbox connection/revoke/reply/sending acceptance was not performed; no messages sent.

## Counts and failures

**61 distinct current-checkout browser scenarios pass** across the latest appropriate suite results: product 4, Radar 7, Phase 2/3 1, real source/Vertex 1, Lead Engine 29, Gmail 2, auth 3, workspace 11, Sheets 1, developer/MCP 2. Identity = source file + full test title; repeated product/auth/phase23 attempts are deduplicated. A scenario is not a count of every assertion or customer requirement.

Retained initial failures: ambiguous MCP locator; genuine opportunity-detail Next 404; test navigations before opportunity create/save response caused undefined record/client disconnect. Fixes use exact modal contract locator, correct real route and polling actual API persistence before reload. The final `product-pages-results.json` has four passes and no failed scenario. Earlier traces/screenshots/logs remain available.

Viewport/no-overflow and keyboard/modal/product-switch checks are bounded acceptance, not a claim of full WCAG certification. No unrelated visual redesign was performed.
