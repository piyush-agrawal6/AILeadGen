# PlaneByte Intent Radar — Growth Intelligence 2.0 Completion Report

## Executive Summary

The Growth Intelligence module has been completely redesigned, restructured, and hardened into a production-grade, 4-section market and customer intelligence workspace.

The previous fragmented 8-tab architecture (`Market Overview`, `Themes`, `Trends`, `Competitors`, `Research`, `Watchlists`, `Reports`, `Saved`) has been consolidated into **4 primary sections**:
1. **Overview** (`/intent-radar/growth`): Executive demand & market intelligence dashboard with 4 core KPIs, Key Insights with verifiable citations, interactive conversation timeline, problem categories, and next growth actions.
2. **Trends & Themes** (`/intent-radar/growth/themes`): 7-column market themes table with evidence citation volume, comparison state, method, saved filtering, and Theme Detail view with exact source quotes and "Create Monitor from Theme" shortcut.
3. **Competitor Intelligence** (`/intent-radar/growth/competitors`): Competitor tracking workspace with aliases, disambiguation notes, filter evidence action, and quick monitor generation.
4. **AI Research** (`/intent-radar/growth/research`): 2-panel workspace with persistent AI Research Assistant (kind, template, scope, ICP context) and structured Reports Viewer (Executive Summary, Evidence-backed Findings, Citations Explorer, Markdown/JSON export).

Retired subpaths now seamlessly redirect to their permanent destinations:
- `/intent-radar/growth/trends` → `/intent-radar/growth/themes`
- `/intent-radar/growth/watchlists` → `/intent-radar/monitors`
- `/intent-radar/growth/saved` → `/intent-radar/saved` (Research Library)
- `/intent-radar/growth/reports` → `/intent-radar/growth/research`

---

## Architecture & Data Discrepancy Resolution

### 1. Zero Discussion Count Root Cause & Fix
- **Root Cause**: In `app/growth_intelligence/analytics.py:55`, `days = scope.days or 7`. When `scope.days == 0` (the default for "All available evidence"), it forced `days = 7` and queried `observed_at >= (now - 14 days)`. Real signals retrieved from public sources had `observed_at` dates from older publication timestamps, causing the query to return 0 records despite signals existing in the database.
- **Fix**: Updated `scope.days == 0` so that it queries without the strict 7-day lower bound, correctly aggregating all available workspace signals.

### 2. Redundant Authentication Queries
- In `app/growth_intelligence/analytics.py`, calling `service.preferences(c)` triggered `_limits_meta` and `billing.overview(c)`, re-querying `organization_memberships` multiple times. Replaced with direct query on `intent_preferences` to fetch `source_retention_days`. All 16 backend tests in `tests/unit/test_growth_intelligence.py` pass within read budgets.

---

## Verification Evidence

- **Frontend Vitest Suite**: 66 test files passed, 275 tests passed (including `dashboard/__tests__/growth-redesign-v2.test.tsx`).
- **Backend Pytest Suite**: 16 passed in `tests/unit/test_growth_intelligence.py`, 38 passed in `tests/unit/test_intent_radar.py`.
- **Next.js Production Build**: Turbopack compiled 85 routes cleanly with zero TypeScript or lint errors.
