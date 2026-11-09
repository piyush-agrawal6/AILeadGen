# Data cleanup report — 2026-11-05

## Applied local generated-file cleanup

The allowlisted maintenance command in `scripts/maintenance/clean_generated.py`
was run first in dry-run mode and then applied. It rejects symlinks and does not
access databases, providers, credentials or environment files.

| Target | Files | Bytes | Treatment |
|---|---:|---:|---|
| `.pytest_cache` | 5 | 64,884 | Archived and removed |
| `dashboard/test-results` | 1 | 45 | Archived and removed |
| `dashboard/.next/cache` | 148 | 528,636,210 | Reproducible compiler cache removed |

The archive `data/backups/heysow-generated-20261105T105658Z.zip` has restrictive
permissions. ZIP integrity was checked, extraction was tested in a temporary
directory and restored file hashes were compared. Compiler cache was explicitly
classified as regenerable; a subsequent frontend build passed.

Machine-readable evidence: `heysow-generated-cleanup-dry-run.json` and
`heysow-generated-cleanup-applied.json` in this directory.

The unused Recharts dependency was removed from the package manifest/lockfile.
The dependency baseline is preserved in `data/backups/heysow-dependency-baseline.zip`.
`heysow-dependency-cleanup.json` records 35 removed lock entries and zero changed
versions among retained packages. No wholesale dependency upgrade occurred.

## Operational records: preserved

No production database rows were deleted, truncated, reset or archived in this
stage. Users, memberships, configuration, credentials, campaigns, sent history,
permanent contacted recipients, DNC, unsubscribes, bounce suppressions, reports,
integration records and migration history remain untouched.

Ownership of historical operational records has not yet been verified for scoped
archival. That work remains pending. Before any such change: inventory by tenant
and record type, classify unknown ownership as retained, create a fresh database
backup, restore-test it separately, review the exact transaction scope and verify
safety/history counts before and after. This local generated-file archive does
not satisfy the database backup requirement.
