# LEADENGINE PHASE 3.5
# PRODUCT UX REFINEMENT + PREMIUM LEAD WORKSPACE + CLIENT-FACING PDF REPORTS

You are Astra acting as the senior product engineer, frontend architect, UX designer, PDF/reporting engineer, and QA owner for the existing LeadEngine repository.

Phase 3 is COMPLETE and production-accepted.

DO NOT rebuild Phase 3.

DO NOT change the cloud architecture.

DO NOT rewrite working authentication, Cloud Run, PostgreSQL, R2, campaign execution, opportunity scoring, or worker infrastructure unless a real regression is discovered while implementing this phase.

This is a focused Phase 3.5 refinement.

The goals are:

```text
1. Improve the Lead Workspace UX
2. Fix filter interaction problems
3. Improve information density in lead rows
4. Make status management faster
5. Add direct client-facing PDF report actions
6. Replace the current HTML audit report with a premium PlaneByte PDF
7. Simplify the New Scan location UX
8. Improve color hierarchy while staying minimal
9. Preserve the premium design direction
10. Keep all existing Phase 3 functionality working
```

---

# 0. CURRENT VERIFIED PRODUCTION BASELINE

Current Phase 3 production state:

```text
Cloud worker                READY
PostgreSQL                  READY
R2                          READY
Google login                READY
Real production campaign    COMPLETED
Opportunity scoring         WORKING
Lead workflow               WORKING
Exports                     WORKING
Security probes             PASSED
```

Current regression baseline:

```text
Python tests          109 passed
Frontend tests         26 passed
Browser tests           3 passed
TypeScript strict       PASS
ESLint                  PASS
Next.js build           PASS
```

Preserve or improve this baseline.

---

# 1. DESIGN DIRECTION

Use the latest approved LeadEngine mockups as the visual reference.

The desired design language is:

```text
premium
minimal
professional
high-information
lightweight
well spaced
clear hierarchy
subtle color
high usability
```

DO NOT produce:

```text
generic shadcn dashboard
Bootstrap-looking admin panel
overly dark/heavy UI
huge empty cards
excessive gradients
neon/glow effects
over-rounded components
decorative charts
AI SaaS visual clichés
```

The interface should feel like a serious internal intelligence product.

The generated reference mockups should be treated as the primary visual direction for:

```text
Lead Workspace
Lead Detail
PDF report
New Scan
```

Do not mechanically copy every pixel.

Match the product quality and interaction principles.

---

# 2. COLOR SYSTEM

Keep the design minimal, but use color intentionally for meaning.

Do NOT make every element colorful.

Use restrained semantic color coding.

## Opportunity score colors

Suggested:

```text
0–39     red / critical
40–59    amber / moderate
60–79    warm yellow / good opportunity
80–100   green / strong opportunity
```

However:

The UI must always communicate:

```text
HIGH SCORE = STRONGER SALES OPPORTUNITY
```

not better website quality.

Use subtle tinted backgrounds, not saturated blocks.

---

# 3. STATUS COLOR CODING

Use consistent status colors everywhere:

```text
NEW
soft blue / neutral blue

SHORTLISTED
green / teal

CONTACTED
blue

REPLIED
purple

NOT_INTERESTED
gray / muted

DO_NOT_CONTACT
red

WON
green

LOST
red / muted red
```

Use:

```text
small dot
subtle tinted pill
clear label
```

Do NOT rely only on color.

Keep labels visible.

---

# 4. LEAD WORKSPACE — FILTER PANEL BUG

Current issue:

The filter panel/modal:

```text
does not close when clicking outside
has no obvious close icon
```

Fix both.

Required behavior:

```text
open filter panel
↓
click outside
↓
panel closes
```

Also:

```text
ESC key closes panel
```

And:

```text
visible X button in top-right
```

Use an accessible:

```text
Dialog / Popover / Sheet
```

pattern appropriate for the layout.

Requirements:

- focus management
- keyboard accessible
- escape to close
- click-outside close
- proper `aria-*`
- no body-scroll bugs
- no focus trapping bugs
- no accidental closure when interacting inside

---

# 5. FILTER PANEL DESIGN

The filter panel should look like the approved mockup.

Use a premium floating panel:

```text
Title: Filters
[X close]

Country
City

Primary opportunity
Vertical

Lead status
Contactability

Seen before
Business size

Minimum Website score
Minimum SEO score
Minimum Security score

Clear all
Apply filters
```

Use a two-column layout where space allows.

On smaller widths:

```text
single column
```

The filter panel should feel deliberate and lightweight.

---

# 6. LEAD WORKSPACE TABLE — RESTRUCTURE

The current table wastes horizontal space and separates information unnecessarily.

Rebuild the row layout.

Preferred columns:

```text
Business

Location

Vertical

Opportunity scores

Primary

Contactability

Status

Report
```

Remove:

```text
Assigned column
```

from the main table.

Assignment remains available in Lead Detail.

---

# 7. BUSINESS CELL — MOVE CONTACT INFO HERE

The Business cell should become the main identity/contact cell.

Display:

```text
Business Name

website URL
phone
email
```

Example:

```text
Ditton Lodge

dittonlodge.co.uk ↗

☎ +44 20 8399 7482
✉ info@dittonlodge.co.uk
```

Use compact inline formatting.

If one field is missing:

do not render empty placeholder noise.

Example:

```text
Ditton Lodge
dittonlodge.co.uk ↗
☎ +44 20 8399 7482
```

If no website:

```text
No official website found
```

Use subtle muted styling.

---

# 8. CONTACT COLUMN

Do NOT show raw contacts in a separate contact column anymore.

The Contactability column should only show:

```text
HIGH
MEDIUM
LOW
UNASSESSED
```

with minimal semantic styling.

Actual email/phone belongs under the business name.

---

# 9. REMOVE SEPARATE SHORTLIST ACTION

The current:

```text
Shortlist
```

action at the end of each row should be removed.

Do not have:

```text
Status = NEW
+
Shortlist button
```

This duplicates functionality.

---

# 10. INLINE STATUS DROPDOWN

Turn the Status column itself into an editable dropdown.

Example:

```text
● New        ▾
```

Clicking it opens:

```text
New
Shortlisted
Contacted
Replied
Not Interested
Do Not Contact
Won
Lost
```

Selecting a value:

```text
updates immediately
persists to backend
updates table without full reload
```

Use optimistic UI only if rollback/error state is handled correctly.

Status update should show:

```text
toast confirmation
```

or subtle inline feedback.

Do not require opening Lead Detail just to change status.

---

# 11. REPORT COLUMN

Add a dedicated:

```text
Report
```

column.

Each row should allow:

```text
Generate PDF
```

if no report exists.

If a report exists:

```text
Download PDF
```

Optionally:

```text
⋮
Regenerate
View details
```

but do not clutter the table.

Primary report action should remain obvious.

---

# 12. TABLE DENSITY

Make rows information-rich but still breathable.

Target:

```text
~72–88px row height
```

depending on content.

Use:

```text
strong business name
muted secondary text
compact icons
tight score chips
minimal borders
subtle row hover
```

Avoid:

```text
giant rows
unnecessary cards inside table
too many buttons
```

---

# 13. OPPORTUNITY SCORES IN TABLE

Show three compact scores:

```text
Website
SEO
Security
```

Example:

```text
W 85
S 38
Sec 72
```

or a compact mini-grid similar to the approved mockup.

Do not use overly large gauges in the table.

Allow sorting by:

```text
Website
SEO
Security
```

Preserve existing sort behavior.

---

# 14. LEAD DETAIL PAGE

The current Lead Detail is functional but should be refined toward the approved mockup.

Do NOT rebuild it unnecessarily.

Improve hierarchy.

Top section:

```text
Business name
Vertical
Location
Website
Phone
Email
Social links

Primary opportunity
Overall lead status
```

Main content:

```text
Opportunity Scores

Website / Redesign
SEO
Basic Security
```

Then:

```text
Why this business
Website evidence
SEO evidence
Security evidence
Technical evidence
Source & provenance
```

Right rail:

```text
Lead Status
Team Workflow
Reports
Notes
```

---

# 15. LEAD DETAIL STATUS

The current status selector should remain.

Keep it visually consistent with the inline table status dropdown.

Do not create two different status-control designs.

---

# 16. REPORT ACTIONS ON LEAD DETAIL

Replace HTML-first behavior.

Primary:

```text
Generate PDF Report
```

Secondary:

```text
Download PDF
```

If no report exists:

```text
Generate PDF Report
```

If report exists:

```text
Download latest PDF

Regenerate
```

Do not present `.html` as the main report format anymore.

---

# 17. REMOVE CLIENT-FACING HTML REPORT AS PRIMARY ARTIFACT

The existing HTML report was useful for technical acceptance but is NOT suitable as the final client deliverable.

Phase 3.5 should switch the client-facing report to:

```text
PDF
```

HTML may remain internally only if required for PDF generation.

Do not expose the raw HTML artifact as the main user download.

---

# 18. PREMIUM PDF REPORT

Create a professional branded PlaneByte report.

This report must be suitable to:

```text
send directly to a prospect
attach to an email
use during a sales call
```

It must NOT look like:

```text
developer debug output
raw HTML dump
generic browser print
basic table export
technical system report
```

The PDF should feel like a professional consulting deliverable.

---

# 19. PDF BRANDING

Use:

```text
PlaneByte
LeadEngine
```

branding.

Include:

```text
PlaneByte logo
LeadEngine identifier
plane-byte.com or actual PlaneByte domain
report date
business name
business location
vertical
```

Use the approved report mockup as the design reference.

---

# 20. PDF PAGE 1 — COVER

Create a premium cover.

Example:

```text
PLANEByte
LeadEngine

DIGITAL GROWTH AUDIT

Digital Growth Opportunities
for Ditton Lodge

Actionable insights to improve
your online presence, visibility,
security and customer acquisition.
```

Include:

```text
Business
Location
Industry / Vertical
Report date
```

Optionally include:

```text
website screenshot
business image
```

only if reliably available.

If not available:

use a high-quality branded abstract layout.

Do NOT fabricate a business image.

---

# 21. PDF PAGE 2 — EXECUTIVE SUMMARY

Include:

```text
Website Opportunity
SEO Opportunity
Security Opportunity
Primary Opportunity
```

Example:

```text
Website     85 / 100
SEO         38 / 100
Security    72 / 100
```

Explain clearly:

```text
Higher opportunity score means stronger opportunity for improvement.
```

Do not imply:

```text
85 = website quality
```

---

# 22. EXECUTIVE SUMMARY COPY

Generate deterministic client-safe explanations from actual findings.

Example:

```text
Our analysis identified several opportunities to improve
Ditton Lodge's digital presence.

The strongest opportunity is the website experience,
followed by security hardening and SEO improvements.
```

Do not invent unsupported claims.

---

# 23. PDF — WEBSITE SECTION

Include:

```text
Current website status
HTTPS
mobile readiness
performance
navigation
conversion actions
contact flow
booking/enquiry flow
technology/CMS if known
```

Then:

```text
Key Website Findings
```

For every issue:

```text
Finding
Evidence
Business impact
Recommendation
```

Example:

```text
Finding
Website unreachable

Evidence
The configured public domain failed repeated bounded requests.

Business impact
Potential visitors may be unable to reach the business online.

Recommendation
Restore or rebuild the website on a reliable modern platform.
```

---

# 24. PDF — SEO SECTION

Include only evidence actually available.

Possible areas:

```text
title
meta description
headings
canonical
robots
sitemap
structured data
local SEO
NAP
location pages
internal links
Lighthouse SEO
```

For each issue:

```text
Issue
Why it matters
Recommended improvement
```

Do NOT claim:

```text
Google ranking position
traffic loss
revenue loss
```

unless actual data exists.

---

# 25. PDF — BASIC SECURITY SECTION

Include passive external observations only.

Possible:

```text
HTTPS
certificate
HSTS
CSP
X-Content-Type-Options
frame protection
Referrer-Policy
Permissions-Policy
cookie security
mixed content
server disclosure
```

Clearly label:

```text
Basic External Security Review
```

Add disclaimer:

```text
This is a passive external configuration review,
not a penetration test or security certification.
```

---

# 26. PDF — BUSINESS IMPACT

Translate technical findings into understandable commercial implications.

Examples:

```text
Visibility
Enquiries
Trust
Conversion
Brand credibility
Reliability
```

Do NOT fabricate numerical business impact.

Use qualitative wording:

```text
may reduce
can affect
could improve
```

instead of:

```text
will increase revenue by 42%
```

---

# 27. PDF — HOW PLANEBYTE CAN HELP

Include:

```text
Recommended Scope
```

based on actual opportunity types.

Possible cards:

```text
Website Redesign

Technical SEO

Local SEO

Security Hardening

Performance Optimization
```

Only include relevant recommendations.

Do NOT include services unsupported by findings.

---

# 28. OPTIONAL PRICING

Do NOT hardcode fictional pricing into the report unless configured.

Support future config such as:

```text
REPORT_SHOW_PRICING=false
```

Default:

```text
false
```

If pricing is disabled:

show:

```text
Recommended engagement
```

without price.

---

# 29. PDF CTA

Final page should include a tasteful CTA:

```text
Let's discuss your digital growth opportunities.
```

Include PlaneByte contact information from configuration.

Example env/config:

```text
PLANEBYTE_WEBSITE=
PLANEBYTE_CONTACT_EMAIL=
PLANEBYTE_PHONE=
```

Do NOT hardcode fake contact details.

---

# 30. PDF GENERATION IMPLEMENTATION

Use a robust production PDF generation path.

Preferred:

```text
HTML/CSS template
↓
headless Chromium / Playwright
↓
PDF
```

or another existing reliable renderer.

Do NOT use a low-quality library that cannot handle:

```text
modern layout
fonts
page breaks
icons
headers/footers
```

The PDF should be:

```text
A4
print-safe
repeatable
deterministic
```

---

# 31. PDF STORAGE

Store PDF in R2.

Suggested object key:

```text
prospects/{prospect_id}/reports/{timestamp}.pdf
```

Persist metadata:

```text
report_id
prospect_id
created_at
created_by
object_key
version
```

Do not overwrite prior reports silently.

---

# 32. REPORT VERSIONING

Allow:

```text
latest report
```

while preserving prior generated reports.

Lead Detail may only show latest by default.

Future report history can come later.

---

# 33. AUTHENTICATED PDF DOWNLOAD

Downloads must remain protected.

Use:

```text
authenticated BFF
```

or:

```text
short-lived signed object URL
```

Do not make R2 bucket public.

---

# 34. TABLE REPORT ACTION

From Lead Workspace:

```text
PDF Report
```

If existing report:

```text
Download PDF
```

If no report:

```text
Generate PDF
```

Show loading state:

```text
Generating…
```

Then automatically switch to:

```text
Download PDF
```

when complete.

---

# 35. NEW SCAN PAGE — KEEP EXISTING GOOD UI

The current New Scan page is already functionally good.

DO NOT redesign it heavily.

Focus on:

```text
color correction
visual hierarchy
consistency
simplification
```

---

# 36. REMOVE DUPLICATE LOCATION TAB

Current issue:

```text
Recommended Markets
Country / Cities
```

are effectively the same UX.

Remove this duplication.

Preferred structure:

```text
Recommended Markets

Custom Location
```

---

# 37. RECOMMENDED MARKETS MODE

Recommended Markets should contain:

```text
Country selector
curated cities
Select Recommended
Select All
Clear
```

Example:

```text
United Kingdom

London
Manchester
Birmingham
Leeds
Bristol
Liverpool
```

No separate `Country / Cities` tab is necessary.

---

# 38. CUSTOM LOCATION MODE

Custom Location should handle:

```text
arbitrary city
arbitrary market
custom location resolution
```

Example:

```text
Scottsdale, Arizona
Edinburgh, Scotland
Nice, France
```

This remains the escape hatch for everything outside curated markets.

---

# 39. NEW SCAN COLOR CORRECTION

The New Scan UI is already structurally good.

Do not turn it into a colorful marketing page.

Use subtle color to differentiate:

```text
selected cards
active steps
opportunity types
quality mode
business-size options
```

Use restrained semantic colors.

---

# 40. NEW SCAN SELECTED STATES

Selected states should be more obvious.

Example:

```text
selected city

subtle green/blue tinted background
stronger border
check icon
```

Do not use giant saturated fills.

---

# 41. NEW SCAN OPPORTUNITY CARDS

Use consistent visual language for:

```text
Website / Redesign
SEO
Basic Security
```

Suggested accent:

```text
Website
blue

SEO
teal/green

Security
purple/indigo
```

Use these consistently throughout:

```text
scan setup
lead table
lead detail
PDF report
```

---

# 42. NEW SCAN VERTICAL CARDS

Keep the current vertical cards.

Improve:

```text
selected state
hover state
icon consistency
spacing
text hierarchy
```

Do NOT add new verticals in this phase.

---

# 43. CAMPAIGN SUMMARY

Keep the sticky summary.

Improve visual hierarchy.

Show:

```text
Locations
Verticals
Opportunity types
Quality
Business size
Target
Execution
```

Use compact sections.

---

# 44. DO NOT ADD FAKE MARKET SCORES

The approved mockup includes city opportunity numbers for visual direction.

Do NOT invent:

```text
London = 95
Manchester = 88
```

unless real data supports it.

If such scores do not exist in the system:

do not display them.

Use:

```text
Recommended
```

instead.

---

# 45. REPORTS & EXPORTS PAGE

Update reports page to distinguish:

```text
Campaign exports
Client PDF reports
```

Campaign exports:

```text
CSV
XLSX
```

Client reports:

```text
PDF
```

Do not mix them conceptually.

---

# 46. REMOVE HTML DOWNLOAD FROM PRIMARY UI

HTML may remain:

```text
internal implementation artifact
```

if required.

But remove:

```text
HTML Report
```

from the main user-facing UI.

User-facing report should be:

```text
PDF Report
```

---

# 47. DARK MODE

The approved mockups use light mode as the primary design reference.

Do NOT remove dark mode.

Ensure every new feature works in:

```text
Light
Dark
System
```

However:

do not compromise light-mode quality just to reuse poor dark-mode tokens.

---

# 48. STATUS DROPDOWN DARK MODE

Verify semantic colors have enough contrast in both modes.

Especially:

```text
NEW
SHORTLISTED
CONTACTED
REPLIED
WON
LOST
```

---

# 49. RESPONSIVE BEHAVIOR

Test:

```text
1366×768
1440×900
1920×1080
```

Lead Workspace table can horizontally scroll at smaller widths if necessary.

Do not collapse business/contact information into unreadable layouts.

Filter panel should become:

```text
drawer / sheet
```

on narrow screens.

---

# 50. ACCESSIBILITY

All new components:

```text
keyboard accessible
visible focus
screen-reader labels
semantic status labels
proper dialogs/popovers
ESC close
click-outside behavior
```

Color must not be the only status indicator.

---

# 51. PERFORMANCE

Do NOT regress server-side pagination.

Do NOT load all leads into browser.

Status updates should update only affected records.

PDF generation should happen server-side/background-safe.

Do not block the browser for PDF generation.

---

# 52. PDF GENERATION STATUS

If generating PDF takes noticeable time:

use states:

```text
Generating
Ready
Failed
```

Do not leave buttons spinning forever.

Persist report-generation failure reason internally.

User message:

```text
Report generation failed.
Try again.
```

Do not expose raw stack traces.

---

# 53. PDF CONTENT SAFETY

Do NOT put internal-only data into client reports:

```text
internal notes
assignment
workflow status
internal opportunity labels
raw database IDs
scanner debug info
source IDs
technical exceptions
```

Client PDF should contain only client-appropriate material.

---

# 54. CLIENT REPORT LANGUAGE

Do not write:

```text
"Your website is terrible."
```

Use professional language:

```text
"We identified several opportunities to improve performance,
visibility and conversion."
```

Keep language factual and consultative.

---

# 55. NO UNSUPPORTED CLAIMS

Do not claim:

```text
malware-free
Google ranking position
lost revenue
traffic volume
exact competitor performance
legal compliance
penetration-test security status
```

unless actual evidence exists.

Security section must explicitly say:

```text
passive external configuration review
```

---

# 56. REPORT GENERATION FROM CURRENT DATA

PDF must use actual persisted evidence from:

```text
business
website profile
findings
Lighthouse
opportunity scores
contacts
```

Do not run a new scan just to generate a report.

If evidence is missing:

```text
Not assessed
```

rather than fabricate values.

---

# 57. WEBSITE-LESS LEADS

For businesses with:

```text
NO_WEBSITE
```

PDF should adapt intelligently.

Do not show:

```text
SEO score N/A
security score N/A
```

as giant empty sections.

Instead:

```text
Primary Opportunity
New Website
```

and explain:

```text
No official website was found in the available public sources.
```

Recommended scope:

```text
Website Design
Local SEO Foundation
Analytics / conversion setup
```

only where appropriate.

---

# 58. UNREACHABLE WEBSITE LEADS

For:

```text
website exists
but unreachable
```

report should explain:

```text
Website Recovery / Redesign
```

and clearly distinguish it from:

```text
No Website
```

---

# 59. TESTS — FILTER PANEL

Add tests:

```text
open filters
click outside closes
ESC closes
X closes
interaction inside does not close
focus restored correctly
```

---

# 60. TESTS — TABLE

Test:

```text
contact data under business name
assigned column absent
shortlist action absent
status dropdown present
status update persists
status colors correct semantically
report action present
```

---

# 61. TESTS — PDF

Add tests for:

```text
PDF generated
PDF header valid
nonzero PDF size
PlaneByte branding present
business name present
opportunity scores present where assessed
website findings present
SEO findings present where assessed
security findings present where assessed
client-only data
R2 object persisted
authenticated download works
```

---

# 62. PDF VISUAL QA

Generate at least:

```text
1 no-website lead PDF
1 reachable website lead PDF
1 unreachable website lead PDF
```

Open them visually.

Check:

```text
page breaks
fonts
logo
icons
tables
spacing
footers
headers
score cards
long text wrapping
URL wrapping
```

Do not consider PDF complete based only on file generation.

---

# 63. LEAD WORKSPACE VISUAL QA

Inspect:

```text
filter closed
filter open
no filters
many active filters
long business names
missing website
missing email
high/medium/low contactability
every status value
```

---

# 64. NEW SCAN VISUAL QA

Inspect:

```text
Recommended Markets
Custom Location

one city
many cities
many verticals
all opportunity types
light mode
dark mode
```

---

# 65. NO PRODUCTION DATA DELETION

Do not delete:

```text
production leads
campaigns
reports
R2 objects
workflow history
```

unless cleaning up explicitly generated test artifacts.

---

# 66. PRESERVE INFRASTRUCTURE

Do not modify unless necessary:

```text
Cloud Run IAM
service accounts
GCP region
Cloud Run worker architecture
R2 configuration
Postgres deployment
Google OAuth
Vercel authentication
```

Phase 3 infrastructure is accepted.

---

# 67. FINAL ACCEPTANCE

Phase 3.5 is complete only when:

```text
[ ] filter closes on outside click

[ ] filter closes on ESC

[ ] filter has visible close icon

[ ] Lead Workspace table redesigned

[ ] contact info moved under business name

[ ] Assigned column removed

[ ] separate Shortlist action removed

[ ] Status is editable inline dropdown

[ ] status colors consistent

[ ] Report column added

[ ] direct PDF generation/download works

[ ] HTML no longer primary client report

[ ] premium PlaneByte PDF implemented

[ ] cover page implemented

[ ] executive summary implemented

[ ] Website section implemented

[ ] SEO section implemented

[ ] Basic Security section implemented

[ ] Business impact implemented

[ ] PlaneByte recommended scope implemented

[ ] client-safe report language

[ ] R2 PDF storage works

[ ] authenticated PDF download works

[ ] New Scan duplicate tab removed

[ ] Recommended Markets simplified

[ ] Custom Location preserved

[ ] New Scan colors/polish improved

[ ] Light mode polished

[ ] Dark mode preserved

[ ] responsive QA passes

[ ] PDF visual QA passes

[ ] no Phase 3 functionality regressed

[ ] all existing tests pass

[ ] new tests pass

[ ] TypeScript strict passes

[ ] ESLint passes

[ ] Next.js production build passes
```

---

# 68. FINAL REPORT

Create:

```text
docs/PHASE_3_5_REPORT.md
```

Include:

```text
before/after UX summary

Lead Workspace changes

filter behavior

table redesign

status workflow

PDF architecture

PDF template structure

New Scan simplification

visual QA

test totals

production deployment

known limitations
```

---

# 69. IMPLEMENTATION ORDER

Follow this order:

```text
1. Inspect existing implementation

2. Fix filter interaction

3. Redesign Lead Workspace table

4. Implement inline status dropdown

5. Implement report column

6. Build PDF generation infrastructure

7. Build premium PlaneByte PDF template

8. Update Lead Detail report actions

9. Update Reports & Exports page

10. Simplify New Scan location tabs

11. Apply color/hierarchy refinements

12. Light/dark QA

13. PDF visual QA

14. Regression tests

15. Production build

16. Deploy

17. Production smoke test

18. Write Phase 3.5 report
```

---

# 70. MOST IMPORTANT PRODUCT PRINCIPLE

Do not redesign for the sake of redesign.

The current product already works.

Phase 3.5 should make it feel:

```text
faster to operate
easier to scan
more professional
more client-ready
more premium
```

without adding unnecessary complexity.

The biggest user-facing improvements are:

```text
better lead rows
faster status management
better filters
client-ready PDF reports
simpler scan setup
```

Focus engineering effort there.

START NOW.

Use the approved mockups as the visual direction.

Preserve all Phase 3 production functionality and data.

Do not rework infrastructure unless a regression requires it.