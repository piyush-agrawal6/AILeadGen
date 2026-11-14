# Functional acceptance — in progress

This document separates isolated tests from provider and production acceptance.
No fake human evaluation, real payment or prospect email is permitted.

## Completed isolated checks at this checkpoint

- First full backend run:995 passed,1 intentional live-mail skip,8 warnings.
  Subsequent backend changes require the second frozen run; this first run is
  not evidence for those later changes.
- Frontend units:157 passed. Marketing units:15 passed.
- Focused backend financial/read regression:62 passed.
- Focused authorization/workspace/read regression:46 passed.
- Latest assistant/usage/read checks:10 passed, including real quota reservation.
- Local PostgreSQL changed-feature subset:13 passed.
- Billing browser regression:2 passed; Growth browser regression:2 passed.
- Six-width product browser matrix: initially4 passed/3 failed, then6 passed/1
  failed. Mobile accessible naming, assistant usage snapshot invalidation and a
  strict test locator were repaired. A final frozen rerun is still required.
- SaaS and marketing production builds passed before the final visual polish;
  the final exact-source build and screenshots must also pass before release.

Exact logs, JUnit XML, JSON browser reports and screenshots are private under
`data/artifacts/verification/final-product/`. Earlier failed logs are retained.

## Real provider evidence

- PayU Live non-chargeable verification probe: HTTP200, expected nonexistent
  transaction. Not a payment, mandate, recurring, currency or refund acceptance.
- Three existing production Vertex usage records are present. The new global
  assistant still needs a bounded real Vertex turn after its worker rollout.
- Existing production source history:3 HN complete checks and2 timeouts; one
  discovery dispatch failure. These are findings, not passed acceptance.
- Current production read latency fails the intended responsive read budget;
  record before/after samples around the verified release.

## Frozen non-chargeable release verification

The final frozen backend source passed **998 tests**, with **1 explicit live-mail
skip**, **0 failures/errors**, and8 warnings in488.72 seconds. Frontend units:
**159 passed**. Type check and the exact frontend production build passed.
The final product browser run passed **7/7**, covering private multi-turn
assistant persistence plus22 product routes at1440/1280/1024/768/390/320 pixels.
The resulting132 route screenshots remain private verification artifacts.
The separate marketing pricing selection browser test passed **1/1** without
submitting a form or payment. These are isolated local results; they do not
certify live PayU checkout or production response time.

## Remaining production flow

Verify exact deployed source → owner Google session → workspace/profile/ICP →
bounded approved-source discovery → original evidence → reviewed AI → save and
opportunity → Growth research/export → monitor/worker/recovery → alert filters →
usage exhaustion/read preservation → MCP/client scope/revocation → billing and
plan-intent persistence → sign-out/sign-in persistence. Preserve all existing
Lead Engine, Gmail and historical financial records throughout.

PayU sandbox/live recurring lifecycle acceptance is a separate blocked gate until
the enabled merchant contract, commercial quotas and charge terms are verified.
Two real reviewers and an adjudicator are still required for the approved
120-case independent AI evaluation. Automated fixtures cannot substitute for
their blind labels or adjudication.
