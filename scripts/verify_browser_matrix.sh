#!/usr/bin/env bash
# Run in a clean verification checkout with locked Python/Node dependencies installed.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
rev=$(git rev-parse HEAD)
test "$rev" = "${GITHUB_SHA:-$rev}"
git diff --quiet HEAD -- app dashboard scripts tests requirements.lock
test -z "$(git ls-files --others --exclude-standard -- app dashboard scripts tests)"
test "$(node -p 'process.versions.node.split(".")[0]')" = 24
test -x .venv/bin/python
cd dashboard
dist=$(mktemp -d .next-matrix-XXXXXXXX)
results="../data/artifacts/verification/ci-browser/$rev"
mkdir -p "$results"
unset LEADENGINE_TEST_DEV LEADENGINE_TEST_BROWSER LEADENGINE_TEST_PYTHON VERCEL_ENV
export APP_ENV=test DATABASE_BACKEND=sqlite DATABASE_URL='' EMAIL_SENDING_ENABLED=false
export HEYSOW_E2E_DIST_DIR="$dist" PLANEBYTE_RELEASE_DIST="$dist"
echo "Browser matrix: source=$rev Node=$(node -v) Playwright=$(node -p 'require("@playwright/test/package.json").version')"
npm run build
test -s "$dist/BUILD_ID"
echo "Next build ID: $(cat "$dist/BUILD_ID")"
pw=node_modules/@playwright/test/cli.js
failed=0
LEAD_ENGINE_AVAILABLE=true node "$pw" test --config=playwright.config.ts --output="$results/legacy" --reporter=list || failed=1
for suite in accounts workspace subscription onboarding destinations; do
  LEAD_ENGINE_AVAILABLE=false PLANEBYTE_RELEASE_JOURNEY="$suite" node "$pw" test --config=playwright.release.config.ts --output="$results/$suite" || failed=1
done
exit "$failed"
