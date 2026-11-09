# ADR0001: Preserve the modular monolith

Status: accepted for the current implementation.

Context: the application already has a Next frontend, a FastAPI/domain backend, SQL adapters and separately executed slow workers. Introducing new databases, queues or microservices would add cost without a measured need.

Decision: preserve that architecture. Extract actual shared contracts incrementally, beginning with module availability and workspace configuration. Keep provider adapters, mail transport and job orchestration in their established boundaries. Do not use documentation or registry metadata to imply that missing billing, MCP, registration or Agent features work.

Consequences: existing integration behavior is preserved; legacy import/caller coupling must be repaired with regression tests. Future service extraction requires measured scale or isolation needs and its own decision record.
