# HeySow simplified workflows

This document separates the intended product flow from the currently available
implementation. It is not an acceptance certificate.

## Authentication: implemented design, limited backend availability

Sign in with the existing verified Google flow, then enter an authorized workspace.
The new light HeySow pages share responsive layout, legal links and accessible
error/loading states. Existing allowlist and session security remain enforced.
Public signup, invitation acceptance and HeySow-managed passwords are not yet
implemented; their pages explain availability and do not claim success.

## Workspace setup and discovery: target flow, incomplete

Create the organization profile and define an ideal customer profile (ICP), then
discover companies matching that profile. Company qualification must be distinct
from having a public email, contact verification and permission to send. A company
may fit the ICP without an email address. Discovery and expensive enrichment must
be explicit, bounded jobs with visible progress and cancellation.

The existing source adapters are retained. Replacing the former contactable-only
default with the complete ICP workflow remains implementation work. Do not claim
this intended behavior is already working end to end.

## Campaigns and outreach: partially implemented

Use a campaign, choose a workspace-owned template, review its personalized copy,
signature and eligible recipients, optionally attach a relevant report, then
explicitly start sending. No mandatory audit, AI-generated copy or universal
static PDF belongs in the default flow.

Workspace template CRUD and report-independent rendering exist. Full campaign
selection/preparation still needs completion and end-to-end validation. Historical
internal experiment templates are not the default library. Permanent contacted
history, unsubscribe, DNC, hard-bounce and other send protections must remain
effective regardless of campaign or template selection.

## Visible navigation

The current simplified sidebar contains Overview, Find prospects, Companies,
Campaigns, Outreach, Schedules and Settings. Do not add unfinished ICP, Agent,
billing or integration actions merely to make navigation appear complete.

## Safe reset and archival

Preserve identity, workspace configuration, integrations and permanent send
safety. Preview only the explicitly selected operational records; back them up
and restore-test before a transactional archive. Unknown records remain retained.
No production operational archival was performed in this implementation stage.
