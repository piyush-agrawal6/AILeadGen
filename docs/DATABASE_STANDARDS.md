# Database standards

Production PostgreSQL remains authoritative. Keep all schema changes in the existing ordered migrations and preserve migration history. This cleanup has not run a production migration or reset, dropped or truncated any database table.

Operational cleanup requires scoped dry-run IDs, verified ownership and history, a fresh restricted backup, a restoration test, a transactional archive plan and preserved safety-ledger checks. Historical snapshots from a prior task do not authorize deletion of newly created records.

Use restrictive foreign keys, explicit UTC timestamps, uniqueness, appropriate indexes, bounded pagination and parameterized queries. Default to archive/read-only for records containing sent messages, replies or audit relationships. Never delete contact/suppression history when removing an operational lead.
