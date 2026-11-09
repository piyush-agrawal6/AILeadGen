# Experimental feature treatment

The internal five-day experiment is no longer a default customer workflow.
Its implementation and historical records are retained for audit and recovery.

| Surface | Current treatment |
|---|---|
| Customer sidebar experiment/results entries | Removed |
| Historical experiment/results pages | Default not found; explicit internal archive access only |
| Experiment and intro-analytics API routes | Default denied server-side; internal owner policy if opted in |
| Experiment scheduler tick | Returns before database/provider work while disabled |
| Fixed-five introduction preparation/preview | Requires explicit internal feature availability |
| Legacy commercial/intro templates in library | Hidden from the default workspace template library |
| Historical template/report/PDF assets | Retained; no bulk deletion |
| AI Agent | Planned, not presented as a working module |

`HEYSOW_INTERNAL_EXPERIMENTS_ENABLED` is a server-side flag with a false default.
No environment file or production flag was changed by this stage. Merely enabling
a flag must not grant another organization archive access. Historical campaigns
are not automatically converted to a new audience or started.

Remaining: replace legacy default qualification and campaign preparation with
the full ICP/workspace-template flow. The new module gate is not a claim that
every legacy default has already been removed from every implementation path.


## Current prospecting separation

The conditional-execution descriptions above are historical. Internal archive
reading never authorizes new experiment work: write APIs and direct preparation
entry points reject it, the scheduler skips experiment schedules, and its tick
does no database/provider work. Lead Engine now uses company/ICP intake and
explicit customer-owned templates with no mandatory PDF. Company qualification
and contact/send eligibility are separate. See
`PLANEBYTE_PROSPECTING_SEPARATION.md` for actual scope and acceptance.
