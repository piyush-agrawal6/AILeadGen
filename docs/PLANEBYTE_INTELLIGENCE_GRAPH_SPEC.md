# PlaneByte Intelligence Graph

## Implemented data contract

Route `/intent-radar/graph` inherits verified workspace/product access. The graph loads the existing `/organization/profile`, Radar `/settings`, bounded `/monitors?page_size=100` and Growth `/competitors` reads. Query keys include the active workspace for graph-specific data.

| Category | Stored context | Editing |
|---|---|---|
| Company profile | Name, website, industry, description | Version-checked existing organization profile update |
| Products & services | Offering name/category/description | Add/edit/remove within existing profile limits |
| Positioning | Positioning and specialties | Same versioned company profile |
| Ideal customers | Target customers and industries | Same profile; detailed ICP editor remains linked |
| Markets & regions | Served countries and headquarters | Same profile |
| Competitors | Existing saved names, aliases, context | Existing competitor workspace |
| Research topics | Radar preferred topics | Existing administrator-protected preferences update |
| Monitoring keywords | Actual saved monitors and criteria | Linked monitor configuration/history |

Every fact is labeled saved, reviewable workspace context, not independently verified. Existing onboarding website proposals retain their original review/provenance mechanism. No AI-generated facts are silently accepted by this graph.

## Interaction

Central company node and category links; category selection updates the detail pane. Search matches category titles and saved values. Zoom is bounded .55–1.5; fit returns to 1. Related values can collapse and are capped at five/category. Structured list exposes bounded actual values; category buttons work without graph navigation. Company edits persist through the existing revision contract; conflicts display an error. Saving does not rewrite research snapshots or silently change monitor criteria/schedules.

## Limits and acceptance

There is no new free-standing pain-point, buying-intent or brand-voice knowledge store. Those concepts remain represented by existing reviewed company/ICP/search/monitor fields where supported. AI auto-proposal and independent verification are not implied by colored nodes. An expanded semantic knowledge model requires an explicit migration and backend contract; it is not declared implemented here.

Reload persistence, selection, structured navigation and responsive layouts are exercised by the product browser suite. Exact results and live status are recorded in the release report.
