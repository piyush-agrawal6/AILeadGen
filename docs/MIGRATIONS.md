# Database migrations and recovery

The current repository has 22 ordered migrations in `app/database/migrations.py`.
Production uses PostgreSQL; isolated development tests use SQLite. No migration
was applied to production during this recovery. No database was reset or truncated.

| Version | Purpose |
|---|---|
| 1–3 | Initial pipeline data and scan persistence |
| 4 | Canonical prospects, identities, campaign/workflow data |
| 5–6 | Versioned client reports and cleanup support |
| 7 | Reviewed mailbox, threads, messages and sales workflows |
| 8 | Tracking facts, opaque tokens and preferences |
| 9–10 | Automation state and manual/scheduled workflow runs |
| 11–12 | Campaign outreach and foundation safety/history |
| 13–15 | Acquisition, experiment history and permanent contacted registry |
| 16 | Organizations, memberships, profiles and ownership backfill |
| 17 | Organization-keyed settings copied from the retained legacy singleton |
| 18 | Personal active-workspace preference, revalidated against membership |
| 19 | Hashed one-use invitations and scoped in-app notification records |
| 20 | Account-scoped workspace-creation idempotency records |
| 21 | Workspace acquisition preferences and ownership on new AI interpretation cache rows |
| 22 | Workspace-owned ideal customer profiles and immutable version history |

Recovery adds **migration 17**, with no edits to historical DDL. It creates
`organization_settings` and copies existing owned settings without dropping or
rewriting the legacy `shared_settings` table. No production migration was run. Repository
creation supports pre-16 schema columns for explicit migration fixtures; current
schema run creation requires an explicit organization. Observation remains strict.
Pre-organization fixtures must seed historical SQL, not bypass modern ownership.

The schema-8 fact backfill now uses migration-only insertion, restricted to a
pre-8 database. It preserves existing SMTP/reply facts without invoking current
membership-dependent runtime services before organizations exist. Runtime tracking
still requires member context or a verified opaque tracking capability.

A dedicated test creates schema 15, inserts historical DNC/contacted/opt-out
records, upgrades through 17 and checks IDs/counts/safety flags, ownership, foreign keys
and repeatability. Additional older-version fixture regressions are tracked in
`HEY SOW_REGRESSION_TRIAGE.md`; do not claim all migration paths pass yet.

## Safety and rollback

Before an approved production migration: capture the exact schema version and row
counts, back up to restricted storage, restore into an isolated database, run
preservation checks and validate the exact release on that copy. PostgreSQL DDL
must remain transactional with the existing migration lock. Stop on any failed
ownership/backfill check; do not advance history manually. SQLite historical DDL
has commit boundaries, so recover a failed local upgrade from its tested backup
rather than rerunning partial DDL blindly. Never drop existing records to resolve
an ownership conflict. Unknown ownership requires review.

## PostgreSQL validation

The PostgreSQL suite is opt-in. Its current 20 cases pass on a private local
PostgreSQL 16.15 instance, including concurrent transactions and actual backup/restore. Run them only with a dedicated test
server and explicit **local/disposable** DATABASE_URL, APP_ENV=test and
RUN_POSTGRES_TESTS=1. The fixture creates/drops only its random test schema.
Never enable the suite using the production URL from root `.env`. Production
migration approval and a verified production backup are separate requirements.

Migration 17 rollback caveat: the legacy singleton is preserved as a historical
snapshot; new settings writes go to organization_settings. Do not simply deploy
an older application after new writes, because it would read stale configuration
and its schema-version check may reject version 17. Prefer a forward fix. Any
rollback requires an approved compatible application or the tested pre-upgrade
restore procedure with explicit reconciliation of subsequent writes. No rollback
or production migration was attempted in this task.

## Migration 18 — gated workspace selection

Adds nullable user_profiles.active_organization_id referencing organizations.
It preserves all users, memberships, profiles, preferences and safety history.
The preference never creates membership and is ignored by the legacy resolver
unless HEYSOW_WORKSPACE_MANAGEMENT_ENABLED is explicitly enabled. It has only
been applied in isolated local tests; PostgreSQL/staging validation is pending.
No production migration or flag change occurred.

## Gated workspace foundation additions

Versions 18–20 are local additive changes, not production-applied migrations.
The 18→19 upgrade has isolated SQLite backup/restore, row-preservation, foreign-key
and repeatability coverage. Version 20 adds only a request ledger; it grants no
membership by itself. Runtime API/workers require the current schema before
resource lookup. PostgreSQL concurrency and rollback approval remain staging gates.
Do not run a production migration or enable the workspace feature solely because
SQLite checks pass.

Migration 21 retains acquisition_preferences as platform provider/copy operational
state, copying its historical configuration only into the existing internal
organization's new preference row. Customer defaults do not inherit that row.
Runtime preference reads expose only source toggles/budgets; provider state is not
customer-writable. AI cache keys change version and include organization/actor;
new records persist organization_id. Historical null-owned rows remain retained.
An isolated 20→21 preservation/idempotency/snapshot-restore test passes; production
and PostgreSQL migration acceptance remain unperformed.

Migration 22 creates only the ICP tables and their indexes/foreign keys. It does
not change lead qualification, campaigns or email eligibility. Isolated SQLite
21→22 upgrade, row preservation, repeated migration and snapshot restore pass.
This does not replace the pending PostgreSQL acceptance.

## Local foundation migrations 23–26

These versions have not been applied in production:

| Version | Additive storage | Preservation evidence |
|---|---|---|
| 23 | organization_setup: reviewed setup, revisions and completed revision | 22→23 isolated SQLite upgrade, snapshot restore and permanent-contact history preserved |
| 24 | organization_domains: hashed DNS challenges and verification history | 23→24 preservation, repeatability and snapshot restore |
| 25 | organization_profile_jobs: scoped website-review jobs and confirmation provenance | 24→25 preservation, repeatability and snapshot restore |
| 26 | organization_ai_usage: per-organization/day/feature logical-request reservations | 25→26 preservation, repeatability and snapshot restore |

All four cases are in `tests/unit/test_foundation_additive_migrations.py`. They
do not delete historical operational/contact data or replace integration storage.
Workers and the API require the latest schema. An older binary is not assumed
compatible after an upgrade; forward fixes or an approved tested restore remain
the rollback options. PostgreSQL acceptance is being run separately and is not
implied by SQLite results.
