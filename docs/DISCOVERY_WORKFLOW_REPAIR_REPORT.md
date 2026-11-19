# Critical Discovery Workflow Repair Report

## Overview
This report documents the forensic audit, contract alignment, and stabilization of the Create Discovery execution workflow (`/intent-radar/discover/new`).

---

## Defects Identified & Permanent Fixes Applied

### 1. Backend Contract Alignment (`from_date` / `to_date`)
- **Root Cause**: The client previously generated ISO timestamp strings with hours, minutes, and milliseconds (e.g. `2026-11-19T10:00:00.000Z`). The backend schema in `app/intent_radar/models.py:61` enforces a date-only type (`from_date: date | None`), causing 422 Unprocessable Entity errors.
- **Fix Applied**: Implemented `formatDateOnly` ensuring all outgoing `from_date` and `to_date` values conform strictly to `YYYY-MM-DD` date strings or `null`.

### 2. Result Limit Constraint Enforcement (`result_limit <= 20`)
- **Root Cause**: Backend schema `app/intent_radar/models.py:64` specifies `result_limit: int = Field(20, ge=1, le=20)`. The frontend dropdown previously offered options of `[10, 20, 50]`. Selecting 50 resulted in immediate backend 422 validation failure.
- **Fix Applied**: Updated dropdown options to `[5, 10, 15, 20]` (default 20), clamping all input values to `Math.min(20, Math.max(1, limit))`.

### 3. Canonical Search Mode Enum
- **Root Cause**: The client previously sent `search_mode: "adhoc"`, violating both SQLite CHECK constraints and the backend Pydantic model (`search_mode: Literal['ai', 'advanced', 'monitor', 'rerun'] = 'advanced'`).
- **Fix Applied**: Aligned `search_mode` to dynamically send `'ai'` when starting from the assistant conversation and `'advanced'` for manual configuration.

### 4. Real Multi-Point Pre-Flight Client Validation
- **Root Cause**: Previous pre-flight checks lacked complete coverage, letting incomplete requests hit the backend.
- **Fix Applied**: Enforced client-side validation checking for:
  - Non-empty search title.
  - At least one active search keyword.
  - At least one configured research source.
  - Valid date bounds (`from_date <= to_date`).
  - Result limit <= 20.
  Validation issues trigger precise, user-friendly Sonner toast messages and auto-scroll to the problematic section.

### 5. AI Assistant & Quota Handling
- **Root Cause**: When daily AI reservations were reached, generic error toasts caused user confusion.
- **Fix Applied**: Gracefully handled `res.quota_exhausted` by displaying an inline informational alert within the chat bubble ("Daily AI assistant limit reached for today. You can continue configuring your discovery search keywords, sources, and filters manually below.") without firing error toasts.

---

## Verification
- Vitest Frontend Suite: 64 test files passed, 262 tests passed.
- Pytest Backend Suite: 38 unit tests passed.
- Next.js Production Build: Built successfully in Turbopack.
