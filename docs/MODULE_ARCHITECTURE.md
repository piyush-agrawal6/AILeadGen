# Module architecture

`app/platform/modules.py` defines immutable module IDs, versions, lifecycle, route prefixes, permission names and usage dimensions. Lead Engine and Sales describe existing domains; the old experiment is disabled; the AI Agent is planned and is not advertised as functioning.

A disabled module retains its data. Customer navigation, direct API access, preparation and scheduled dispatch must all honor its availability. Legacy archive access additionally requires the internal workspace and owner role. No client-supplied module or workspace flag grants access.

Future entitlements, usage metering and events must reuse central services; do not introduce microservices or per-module identity systems. New capabilities need an explicit service interface, scoped storage, bounded jobs, authorization tests and documented lifecycle before changing their registry status.


## Prospecting separation — 2026-11-06

Lead Engine execution uses `app/prospecting` company intake and workspace-owned
templates. Search Visibility is PLANNED and Security Assessments is DISABLED.
The saved-HTML parser and historical report validation have explicit ownership
under `app/search_visibility`, with compatibility imports for older consumers.
There are no new assessment routes or jobs. See
`PLANEBYTE_PROSPECTING_SEPARATION.md` for the call-path/dependency audit, data
preservation policy, API compatibility and actual verification evidence.
