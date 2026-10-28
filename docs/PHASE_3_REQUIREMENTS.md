# LEADENGINE PHASE 3
# SHARED CLOUD LEAD INTELLIGENCE PLATFORM
# WEBSITE + SEO + BASIC SECURITY LEADS
# PREMIUM NEXT.JS UI
# PRODUCTION HARDENING & DEPLOYMENT

You are Astra acting as the senior principal engineer, product architect, security engineer, data engineer, UI/UX engineer, DevOps engineer, and QA owner for the existing LeadEngine repository.

This is an EXISTING production-quality codebase.

DO NOT rebuild it from scratch.

DO NOT create a second application beside it.

DO NOT discard working Phase 1/Phase 2 functionality.

Work autonomously through the complete phase.

The repository itself is the source of truth.

---

# 0. CURRENT VERIFIED PHASE-2 STATE

Phase 2 already implemented:

- Python LeadEngine core pipeline
- Overture Maps discovery
- OpenStreetMap discovery
- market resolution
- normalization
- deterministic vertical validation
- chain/franchise filtering
- social-URL re-routing
- SSRF-safe website probing
- multi-page crawler
- contact extraction
- technology detection
- technical/SEO checks
- Lighthouse
- deterministic scoring
- exports
- HTML reports

Application layer:

- FastAPI
- typed Pydantic schemas
- REST APIs
- persistent pipeline events
- SSE
- cancellation
- resume/checkpoints
- `LocalScanExecutor`

Dashboard:

- Next.js App Router
- TypeScript strict
- Tailwind
- TanStack Query
- TanStack Table
- Recharts
- Sonner
- next-themes

Current Phase-2 verification baseline:

```text
Python pytest      31 passed
Frontend tests      8 passed
TypeScript          0 errors
ESLint              0 errors
Next production     build passes
```

Current database:

```text
SQLite
data/lead_engine.db
```

Current dashboard framework:

```text
Next.js 14.2.35
React 18
```

This framework version is no longer acceptable for Phase 3.

---

# 1. PHASE-3 PRODUCT GOAL

Transform LeadEngine from:

```text
local single-machine prospecting application
```

into:

```text
shared hosted lead-intelligence platform
```

for two PlaneByte founders.

LeadEngine Phase 3 should answer:

```text
Which SMBs should we contact?

Why?

Do they need:

- a website/redesign?
- SEO?
- basic website-security hardening?

How strong is each opportunity?

Can we contact them?

Have we already contacted them?

Who on our team owns the lead?
```

Keep the commercial scope focused.

DO NOT turn this into a huge CRM.

---

# 2. NON-NEGOTIABLE FEATURE SCOPE

Phase 3 includes:

```text
1. Technology modernization
2. Security hardening

3. Premium UI/UX redesign

4. Seven target vertical families

5. Multi-country / multi-city targeting

6. Website opportunity scoring

7. SEO opportunity scoring

8. Basic passive cybersecurity scoring

9. SMB / established-business classification

10. Cross-scan lead identity / duplicate suppression

11. Lightweight lead workflow
12. Assignment
13. Notes

14. Two-user authentication

15. PostgreSQL production storage

16. Cloud object storage

17. Cloud-hosted FastAPI

18. Cloud scan execution

19. Vercel dashboard deployment

20. Production QA / security / deployment verification
```

---

# 3. DO NOT ADD THESE FEATURES

Explicitly out of scope:

```text
automatic email sending
Gmail integration
cold-email campaigns
AI-generated outreach
OpenAI
Gemini
Claude
proposal generation
billing
subscriptions
public registration
public SaaS signup
full organizations/tenants
advanced CRM
sales pipelines
AEO
backlink intelligence
Common Crawl analysis
accessibility scanner
active vulnerability scanning
penetration testing
government company feeds
mobile apps
```

Do not introduce feature creep.

---

# 4. PHASE 3A — AUDIT BEFORE MODIFYING ANYTHING

Before implementing features:

Read:

```text
README.md
docs/FINAL_REPORT.md
docs/PHASE_2_REPORT.md
```

Inspect:

```text
dashboard/package.json
dashboard/package-lock.json
dashboard/next.config.*
dashboard/tsconfig.json

pyproject.toml
requirements.txt

app/api/
app/database/
app/pipeline/
app/qualification/
app/audit/
app/enrichment/
app/discovery/
app/exports/
config/
tests/
```

Run the complete baseline:

```powershell
pytest

cd dashboard
npm ci
npm run typecheck
npm run lint
npm run test
npm run build
```

Run:

```powershell
python lead_engine.py doctor
```

Document the baseline.

Do NOT begin migrations until the baseline is understood.

---

# 5. PHASE 3A — TECHNOLOGY MODERNIZATION

This is mandatory and happens BEFORE major feature development.

The existing dashboard uses Next.js 14.

Upgrade it.

At implementation time, check official framework documentation and support status.

Target:

```text
Next.js:
latest stable patched Next.js 16.x Active-LTS release

Node.js:
current Node 24 LTS release

React:
official version supported by selected Next.js 16 release

TypeScript:
current stable compatible release
```

Also audit and safely modernize:

```text
Tailwind CSS
TanStack Query
TanStack Table
Recharts
Zod
React Hook Form
next-themes
Sonner
Lucide
testing libraries
ESLint configuration
```

Requirements:

- no Next.js 14;
- no deprecated Next.js APIs;
- no canary packages;
- no prerelease packages without documented justification;
- no abandoned dependencies;
- no unnecessary dependency duplication.

Follow official Next.js 16 migration guidance.

If Next.js 16 changes conventions used by the current application, migrate them properly rather than using compatibility hacks.

Examples include routing/runtime/build/proxy conventions where applicable.

---

# 6. DEPENDENCY SECURITY

Audit:

```text
npm outdated
npm audit

Python installed dependencies
Python vulnerability status
```

Do NOT blindly execute:

```text
npm audit fix --force
```

Instead:

```text
identify
understand
upgrade intentionally
test
```

Production dependency policy:

```text
No unsupported framework majors.
No EOL runtimes.
No known critical/high vulnerabilities left unaddressed
without explicit documented mitigation.
```

Use lockfiles.

Production Node installs must be reproducible via:

```text
npm ci
```

---

# 7. NODE VERSION

Add:

```text
.nvmrc
```

and/or package engines:

```json
"engines": {
  "node": ">=24 <25"
}
```

unless official Next.js compatibility requires another currently supported LTS.

Do not target Node Current for production merely because it is newer.

---

# 8. WEB SECURITY HARDENING

Perform a complete Next.js security hardening pass.

Implement or verify:

```text
Content-Security-Policy

nonce-based CSP where appropriate

Strict-Transport-Security

X-Content-Type-Options: nosniff

frame-ancestors or equivalent clickjacking protection

Referrer-Policy

Permissions-Policy
```

Review:

```text
script-src
style-src
connect-src
img-src
font-src
frame-src
object-src
base-uri
form-action
```

Make policy compatible with:

```text
Vercel
Google OAuth
FastAPI proxy
application assets
```

without falling back to an unnecessarily permissive CSP.

Do NOT use:

```text
unsafe-eval
```

in production unless unavoidable and documented.

---

# 9. SECRET BOUNDARIES

No production secret may appear in:

```text
NEXT_PUBLIC_*
browser bundle
client component props
HTML
logs
diagnostic UI
API responses
```

Audit all environment-variable usage.

Only genuinely public configuration may be exposed client-side.

---

# 10. AUTHENTICATION

Add Google authentication.

This application currently has only two authorized users.

No registration.

No invite flow.

No password login.

No public signup.

Use the current officially supported Auth.js implementation compatible with Next.js 16.

Authentication requirements:

```text
Google OAuth

email_verified must be true

email must appear in ALLOWED_USER_EMAILS
```

Otherwise deny access.

Protected routes include:

```text
/
scans
leads
reports
settings
system
```

Unauthenticated users:

```text
→ /login
```

Create a premium minimal login page.

---

# 11. AUTHORIZATION MUST BE SERVER-SIDE

Frontend route guards are NOT sufficient.

Every privileged operation must be server-authorized.

Examples:

```text
create scan
cancel scan
resume scan
modify lead status
assign lead
write note
change settings
download protected report
```

must require authenticated user context.

---

# 12. NEXT.JS → FASTAPI SECURITY MODEL

Do NOT expose the production FastAPI API as an unauthenticated browser backend.

Preferred architecture:

```text
Browser
   ↓
Authenticated Next.js
   ↓
Next.js server/BFF route
   ↓
signed internal request
   ↓
FastAPI
```

Use:

```text
LEADENGINE_API_SIGNING_SECRET
```

server-side only.

Design a simple robust signed-request scheme using:

```text
timestamp
nonce/request ID
method
path
body hash
HMAC
```

or a short-lived signed internal JWT if that is cleaner.

Protect against replay.

FastAPI verifies signature before privileged API processing.

Browser must never receive the signing secret.

Production browser should normally talk to same-origin Next.js APIs rather than directly to Cloud Run.

---

# 13. FASTAPI SECURITY HARDENING

Implement/verify:

```text
strict Pydantic schemas

bounded request sizes

bounded pagination

allowed sort fields

no arbitrary SQL

parameterized SQL

no shell=True

no unsafe command construction

safe filenames

safe R2 object keys

safe redirects

safe URL processing

SSRF controls

private-IP blocking

metadata-IP blocking

redirect validation

CORS restrictions

sanitized production errors
```

Do not expose Python traceback to normal users.

---

# 14. SEVEN TARGET VERTICAL FAMILIES

The primary Phase-3 target verticals are:

```text
HOME SERVICES
├ HVAC
├ Plumbing
├ Roofing
├ Electrical
└ General Contractors

DENTISTS

AUTO REPAIR

REAL ESTATE / PROPERTY MANAGEMENT
├ Real Estate Agencies
├ Brokerages
├ Property Management
└ Property Developers

LEGAL
├ Law Firms
└ Attorneys

HOTELS / HOSPITALITY
├ Independent Hotels
├ Boutique Hotels
├ Resorts
├ Guest Houses
└ Vacation-Rental Operators

VETERINARY
├ Veterinary Clinics
└ Animal Hospitals
```

Preserve existing Restaurant support for backward compatibility.

Do NOT delete old restaurant scans/data/tests.

Restaurant does not need to be a Recommended Phase-3 vertical.

---

# 15. VERTICAL TAXONOMY

For every new vertical define:

```text
Overture categories
OSM tags
positive-name signals
negative-name signals
vertical validation rules
vertical-specific audit rules
```

Update:

```text
config/verticals.yaml
VerticalValidator
discovery resolver
API schemas
UI
tests
```

Do not rely on fuzzy business names alone.

Source taxonomy/tag evidence remains primary.

---

# 16. HOME SERVICES

Support:

```text
HVAC
Plumbing
Roofing
Electrical
General Contractors
```

Detect relevant website conversion features:

```text
service pages
service-area pages
quote/request-service CTA
phone CTA
emergency service content
contact forms
location/service coverage
LocalBusiness schema
```

---

# 17. DENTISTS

Check relevant signals:

```text
appointment CTA
service pages
location page
phone/contact
LocalBusiness/Dentist schema where available
local SEO
treatment/service structure
```

---

# 18. AUTO REPAIR

Check:

```text
service pages
appointment/booking CTA
phone CTA
location
hours
LocalBusiness/AutomotiveBusiness schema
local SEO
```

---

# 19. REAL ESTATE / PROPERTY MANAGEMENT

Preserve and improve:

```text
property search/listings
enquiry forms
location/neighborhood pages
lead capture
RealEstateAgent/LocalBusiness schema
property-management services
```

---

# 20. LEGAL

Check:

```text
practice-area pages
location pages
consultation CTA
contact flow
attorney/law-firm structured data where available
local SEO
```

Never infer legal credentials that the website/source does not state.

---

# 21. HOTELS / HOSPITALITY

Preserve and improve:

```text
room pages
direct booking
booking CTA
Hotel/LodgingBusiness schema
location/destination pages
contact
mobile booking UX
```

Prefer independent/small operators.

---

# 22. VETERINARY

Check:

```text
appointment CTA
emergency/contact information
service pages
location
hours
LocalBusiness/VeterinaryCare structured data
local SEO
```

---

# 23. GEOGRAPHIC TARGETING

Replace the current simple market selector with:

```text
Recommended Markets

Country / Cities

Custom Location
```

The user must be able to select multiple cities.

---

# 24. INITIAL COUNTRY PRESETS

Add:

```text
United States
United Kingdom
Canada
Australia
France
Germany
```

These are convenience presets.

Do not hardcode the LeadEngine engine itself to these countries.

Custom location resolution must continue working globally.

---

# 25. INITIAL CURATED CITIES

Use the following starter presets.

United States:

```text
Miami
Fort Lauderdale
Dallas
Fort Worth
Houston
Atlanta
Raleigh
Charlotte
Denver
Nashville
Austin
Phoenix
```

United Kingdom:

```text
London
Manchester
Birmingham
Leeds
Bristol
Liverpool
```

Canada:

```text
Toronto
Vancouver
Calgary
Montreal
Ottawa
```

Australia:

```text
Sydney
Melbourne
Brisbane
Perth
Adelaide
```

France:

```text
Paris
Lyon
Nice
Marseille
Bordeaux
```

Germany:

```text
Berlin
Munich
Hamburg
Frankfurt
Cologne
```

Store presets as configuration/data, not giant frontend hardcoding.

Each city should include:

```text
display name
canonical lookup name
country
country code
priority
```

---

# 26. COUNTRY/CITY UX

Example:

```text
Country

United States

Cities

☑ Miami
☑ Dallas
☑ Atlanta
☐ Houston
☐ Denver

[ Select Recommended ]
[ Select All ]
[ Clear ]
```

Support city search.

Selected cities appear as compact removable tokens/chips.

Do NOT implement literal nationwide scanning in this phase.

Selecting a country should show its curated target cities.

Custom Location covers locations outside the presets.

---

# 27. MULTI-VERTICAL SCANS

Allow:

```text
☑ Home Services
☑ Dentists
☐ Auto Repair
☑ Real Estate
...
```

One scan request may include several cities and several verticals.

Do not create a fragile giant single pipeline execution.

---

# 28. SCAN CAMPAIGN MODEL

Introduce the concept:

```text
Scan Campaign
```

A campaign represents the user's one UI action.

Example:

```text
Cities:
Miami
Dallas

Verticals:
Dentists
Home Services
```

Backend expands this into child pipeline runs:

```text
Miami × Dentist
Miami × Home Services
Dallas × Dentist
Dallas × Home Services
```

Preserve existing `pipeline_runs`.

Add a parent:

```text
scan_campaigns
```

with:

```text
id
created_by
status
configuration_json
created_at
started_at
completed_at
target_total
aggregate counters
```

Add:

```text
campaign_id
```

to pipeline runs.

Existing historical Phase-2 runs must remain readable.

---

# 29. CAMPAIGN PROGRESS

Campaign UI aggregates child runs:

```text
4 child scans

2 complete
1 running
1 queued

Discovered
Qualified
Website Leads
SEO Leads
Security Leads
```

Allow drill-down into individual city/vertical runs.

---

# 30. OPPORTUNITY TYPES

New Scan:

```text
☑ Website / Redesign
☑ SEO
☑ Basic Cybersecurity
```

Default all three.

A business can qualify for multiple opportunity types.

---

# 31. SHARED CRAWL

Do NOT crawl the same website independently three times.

Architecture:

```text
Website
   ↓
Shared Fetch/Crawl
   ↓
┌─────────────────┬─────────────────┬─────────────────┐
Website Analyzer  SEO Analyzer      Security Analyzer
```

Reuse:

```text
HTML
headers
cookies
links
structured data
technology
contact data
```

SEO mode may request additional pages.

---

# 32. WEBSITE OPPORTUNITY SCORE

Create:

```text
website_opportunity_score
0–100
```

High score means:

```text
strong sales opportunity for new website/redesign
```

Consider deterministic evidence such as:

```text
NO_WEBSITE
UNREACHABLE_WEBSITE
HTTP_ONLY
NO_MOBILE_VIEWPORT
VERY_POOR_PERFORMANCE
BROKEN_NAVIGATION
BROKEN_LINKS
NO_PRIMARY_CTA
NO_CONTACT_FLOW
POOR_VERTICAL_CONVERSION_FLOW
PDF_ONLY_CRITICAL_CONTENT
OUTDATED/LEGACY IMPLEMENTATION
```

Do not score purely on subjective aesthetics.

---

# 33. WEBSITE CLASSIFICATION

Examples:

```text
80–100 Strong Website Opportunity
60–79  Good Website Opportunity
40–59  Possible Website Opportunity
<40    Low Website Opportunity
```

Possible services:

```text
NEW WEBSITE

WEBSITE REDESIGN

WEBSITE REDESIGN + PERFORMANCE

WEBSITE + LOCAL SEO
```

---

# 34. SEO OPPORTUNITY SCORE

Create:

```text
seo_opportunity_score
0–100
```

High score means:

```text
strong opportunity to sell SEO
```

Do NOT confuse it with:

```text
SEO quality score
```

The UI must clearly communicate:

```text
Higher opportunity = larger problem / sales opportunity.
```

---

# 35. TECHNICAL SEO

Check:

```text
title presence/quality
meta descriptions
H1/H2 structure
canonical
robots.txt
sitemap.xml
noindex/indexability
HTTP status codes
broken internal links
redirect chains
404 links
HTTP/HTTPS consistency
www/non-www consistency
structured data
image alt coverage
internal linking
mobile signals
performance signals
```

Do not claim actual Google rankings unless data supports them.

---

# 36. LOCAL SEO

Check deterministic signals:

```text
business name
address
phone

NAP consistency

LocalBusiness schema
vertical-specific schema

location page

service-area/location pages

city references

hours

contact page
```

Compare where possible:

```text
Overture / OSM
vs
website
vs
structured data
```

Do not flag a mismatch unless normalization shows a real discrepancy.

---

# 37. SEO CRAWL DEPTH

Standard crawl remains bounded.

Example:

```text
CRAWL_MAX_PAGES=8
```

When SEO analysis requires deeper evidence:

```text
SEO_CRAWL_MAX_PAGES=30
```

Reuse existing pages first.

Only fetch additional pages when required.

Maintain:

```text
same-domain restriction
page-size limits
timeouts
robots-aware behavior
bounded concurrency
```

---

# 38. BASIC CYBERSECURITY OPPORTUNITY

Create:

```text
security_opportunity_score
0–100
```

This is BASIC, PASSIVE, EXTERNAL website-security analysis.

Do not turn lead generation into penetration testing.

Check:

```text
HTTPS

certificate validity

HTTP → HTTPS redirect

HSTS

Content-Security-Policy

X-Content-Type-Options

frame protection

Referrer-Policy

Permissions-Policy

cookie Secure flag

cookie HttpOnly flag

cookie SameSite

mixed active content

X-Powered-By disclosure

server/version disclosure

insecure HTML form actions
```

Reuse HTTP/crawl data.

---

# 39. STRICT SECURITY SCAN BOUNDARY

DO NOT perform during lead discovery:

```text
SQL injection payloads
XSS payloads
authentication attacks
brute forcing
credential testing
port scanning
directory brute forcing
active ZAP
Nuclei active templates
exploit attempts
DoS
```

No intrusive security testing.

---

# 40. OPPORTUNITY DATA MODEL

Do not overload the Phase-2 legacy score indefinitely.

Introduce versioned opportunity scoring.

Suggested model:

```text
opportunity_scores

id
business_id
run_id

website_opportunity_score
seo_opportunity_score
security_opportunity_score

primary_opportunity
secondary_opportunity

contactability_level

scoring_version

created_at
```

Adapt to repository conventions.

Preserve historical Phase-2 scoring data.

---

# 41. PRIMARY / SECONDARY OPPORTUNITY

Example:

```text
Website   24
SEO       88
Security  41

Primary:
SEO

Secondary:
Security
```

Use deterministic ordering and minimum thresholds.

---

# 42. CONTACTABILITY

Calculate:

```text
HIGH
MEDIUM
LOW
```

from public contact evidence.

Example:

```text
public email + phone
→ HIGH

phone/contact form
→ MEDIUM

social only
→ LOW
```

Do not fabricate contact information.

---

# 43. BUSINESS SCALE / ESTABLISHED PLAYER FILTER

Create deterministic scale classification:

```text
LOCAL
SMALL_GROUP
REGIONAL
ENTERPRISE
KNOWN_CHAIN
```

Target defaults:

```text
LOCAL          ✓
SMALL_GROUP    ✓
REGIONAL       optional
ENTERPRISE     ✕
KNOWN_CHAIN    ✕
```

Use:

```text
known chain lists
known chain domains
brand frequency
same domain across locations
same brand across cities
source/location count
```

Suggested heuristic only:

```text
1–5 locations
→ local/small group

6–15
→ regional candidate

16+
→ established candidate
```

Do NOT use location count as the sole signal.

Preserve chain explanation/confidence.

---

# 44. LEAD QUALITY MODES

Add:

```text
Maximum Volume

Balanced

High Intent
```

Default:

```text
Balanced
```

Map them to deterministic configuration.

For example:

```text
MAXIMUM VOLUME

lower opportunity threshold
contact optional
```

```text
BALANCED

medium opportunity threshold
contact preferred
```

```text
HIGH INTENT

high opportunity threshold
public contact required
uncertain verticals excluded
enterprise/chain excluded
```

Centralize configuration.

Do not scatter magic values through UI/backend.

---

# 45. GLOBAL PROSPECT IDENTITY

Phase 3 needs persistent lead identity across scans.

If the same company appears next week, it must not look like a brand-new unrelated lead.

Create a canonical identity layer.

Use evidence such as:

```text
normalized root domain
normalized phone
source IDs
normalized name + normalized address/location
```

Prefer strong identifiers.

Avoid false merges.

Introduce a table such as:

```text
business_identities
```

or an equivalent clean architecture.

Store:

```text
first_seen_at
last_seen_at
times_discovered
```

Link scan-specific business observations to the canonical identity.

Do not destroy Phase-2 business records.

---

# 46. NEW LEAD FILTERING

Support:

```text
New Leads Only

New + Previously Seen

All
```

New means:

```text
first discovered during the relevant campaign/window
```

Do not show previously known leads as new simply because another scan rediscovered them.

---

# 47. LIGHTWEIGHT LEAD WORKFLOW

Add:

```text
NEW

SHORTLISTED

CONTACTED

REPLIED

NOT_INTERESTED

DO_NOT_CONTACT

WON
```

This is not a full CRM.

Persist status on the canonical lead/prospect identity.

---

# 48. ASSIGNMENT & NOTES

Two users need collaboration.

Support:

```text
Assigned To
```

and:

```text
Notes
```

For Phase 3, simple notes are sufficient.

No threads.

No task system.

No notifications.

Track:

```text
created_by
updated_by
assigned_to
updated_at
```

where relevant.

---

# 49. DATABASE MIGRATION — SQLITE TO POSTGRESQL

Production/shared operation requires PostgreSQL.

Use:

```text
Neon PostgreSQL
```

via:

```text
DATABASE_URL
```

Keep SQLite compatibility where useful for:

```text
unit tests
offline/local development
legacy migration
```

Do NOT let the application remain architecturally dependent on SQLite-specific behavior.

---

# 50. DATABASE IMPLEMENTATION STRATEGY

Inspect the current repository layer first.

Do NOT automatically rewrite the entire database layer with a large ORM.

Prefer the smallest robust migration path.

Options may include:

```text
psycopg 3
portable repository SQL
database backend abstraction
```

Use an ORM only if repository analysis shows a clear benefit.

Maintain parameterized queries.

Maintain transactions.

Maintain foreign-key integrity.

---

# 51. SQLITE → POSTGRES DATA MIGRATION

Create an idempotent migration utility such as:

```text
scripts/migrate_sqlite_to_postgres.py
```

It should migrate:

```text
businesses
website profiles
contacts
Lighthouse results
findings
lead scores
pipeline runs
pipeline events
Phase-3 data
```

where applicable.

Validate counts.

Produce a migration report.

Never delete the original SQLite database.

---

# 52. POSTGRES MIGRATIONS

Continue versioned schema migrations.

Production startup must NOT unpredictably perform destructive migrations.

Provide an explicit migration command.

Document:

```text
development migrations
production migrations
rollback/recovery expectations
```

---

# 53. AUTH USERS

Create minimal internal users representation if required for assignment/audit data.

Store:

```text
email
display name
avatar URL
role
last login
```

Both initial users:

```text
ADMIN
```

Authorization eligibility still comes from:

```text
ALLOWED_USER_EMAILS
```

No public user creation.

---

# 54. PREMIUM UI / UX — NON-NEGOTIABLE

Phase 3 UI must NOT look like:

```text
generic admin template
basic shadcn dashboard
Bootstrap dashboard
AI-generated SaaS template
developer CRUD panel
```

The quality benchmark is the level of care found in:

```text
Linear
Vercel
Stripe Dashboard
Raycast
high-end security/data products
```

Do NOT copy them.

Use them as quality references.

---

# 55. UI PRODUCT CHARACTER

LeadEngine should feel:

```text
premium
minimal
calm
professional
high-information
fast
trustworthy
intentional
easy to understand
```

The product should look expensive because of:

```text
hierarchy
spacing
typography
interaction quality
information architecture
```

not because of gradients and effects.

---

# 56. AVOID UI SLOP

Do NOT use:

```text
giant gradients
random glowing cards
glass everywhere
huge marketing headings
massive unused whitespace
rainbow dashboards
meaningless charts
every section inside oversized rounded cards
excessive shadows
decorative animation
```

This is an operational product.

---

# 57. DESIGN SYSTEM

Build/refine a coherent design system.

Use:

```text
clear typography hierarchy
neutral surfaces
subtle borders
restrained shadows
consistent spacing
consistent radii
compact high-quality controls
meaningful semantic colors
consistent icons
```

Support:

```text
Light
Dark
System
```

Dark mode must be intentionally designed.

---

# 58. LOGIN UX

Create a polished minimal login page.

It should communicate:

```text
LeadEngine
PlaneByte internal lead intelligence
Sign in with Google
```

No marketing landing page.

No public signup.

---

# 59. OVERVIEW DASHBOARD

Refocus Overview around useful actions.

Primary KPIs:

```text
New Leads

High-Intent Leads

Website Opportunities

SEO Opportunities

Security Opportunities

Uncontacted Leads
```

Also:

```text
Running Campaigns
Recent Campaigns
Opportunity Mix
Lead Status
Top Target Markets/Verticals
```

Avoid meaningless vanity metrics.

---

# 60. NEW SCAN UX

The New Scan flow should be one of the best parts of the product.

A normal user should configure a scan in under one minute.

Primary configuration:

```text
Location

Verticals

Opportunity Types

Lead Quality

Target

Start Scan
```

Advanced technical settings hidden by default.

---

# 61. NEW SCAN LAYOUT

Concept:

```text
NEW LEAD SCAN

Location
────────────────────────

Recommended Markets
Country / Cities
Custom Location

Country
[ United States ]

Cities
[ Miami ] [ Dallas ] [ Atlanta ]


Verticals
────────────────────────

☑ Home Services
☑ Dentists
☐ Auto Repair
☑ Real Estate / Property Management
☐ Legal
☐ Hotels / Hospitality
☐ Veterinary


Opportunities
────────────────────────

☑ Website / Redesign
☑ SEO
☑ Basic Security


Business Size
────────────────────────

☑ Local
☑ Small Group
☐ Regional
☐ Enterprise
☐ Known Chains


Lead Quality
────────────────────────

○ Maximum Volume
● Balanced
○ High Intent


Results
────────────────────────

● New Leads Only
○ Include Previous


Target Qualified Leads
[ 250 ]

[ Start Scan ]
```

Do not copy this mechanically if a better UX emerges.

---

# 62. SCAN PREVIEW

Before starting, show a concise summary:

```text
3 cities
4 verticals
3 opportunity analyzers

Balanced quality
Local + Small Group

Target:
250 qualified leads

Estimated child scans:
12
```

For cloud mode show:

```text
Cloud execution
Configured worker parallelism
Safety limits
```

Do not invent precise time/cost estimates without data.

---

# 63. LEADS TABLE

This is the core operational screen.

Prioritize:

```text
Business

Location

Vertical

Website Opportunity

SEO Opportunity

Security Opportunity

Primary Opportunity

Contactability

Status

Assigned To
```

Allow optional technical columns.

High scores should stand out.

Low scores should visually recede.

---

# 64. LEAD FILTERS

Provide high-quality server-side filters:

```text
Country
City
Vertical
Opportunity Type
Minimum Website Score
Minimum SEO Score
Minimum Security Score
Primary Opportunity
Contactability
Business Size
Lead Status
Assigned To
Campaign
New / Previous
```

Active filters must be obvious.

Provide:

```text
Clear All
```

Persist useful state in URL parameters.

---

# 65. LEAD DETAIL WORKSPACE

Do not make lead detail feel like a database record.

Information hierarchy:

```text
Business summary

Primary Opportunity

Opportunity scores

Recommended service

Top findings

Contact information

Website analysis

SEO analysis

Security analysis

Technical evidence

Source/provenance

Lead status

Assignment

Notes
```

Do not bury primary information behind excessive tabs.

---

# 66. SCORE UX

Example:

```text
Website        24

SEO            88  HIGH

Security       41
```

Clearly label them:

```text
Opportunity Scores
```

Explain:

```text
Higher = stronger service opportunity
```

---

# 67. LIVE CAMPAIGN UX

Show:

```text
campaign status
child runs
current stages
real counters
qualified leads
errors
elapsed time
```

Example:

```text
Miami — Dentist             Complete
Miami — Home Services       Running
Dallas — Dentist            Running
Dallas — Home Services      Queued
```

No fake progress.

---

# 68. LEAD WORKFLOW UX

Make primary actions visible:

```text
Shortlist
Mark Contacted
Mark Replied
Assign
Add Note
Open Website
Generate Report
```

Do not bury every action inside an overflow menu.

---

# 69. EMPTY / LOADING / ERROR UX

Premium UX includes:

```text
skeletons
stable layout
meaningful empty states
actionable errors
small contextual loaders
```

Avoid:

```text
full-page generic spinner
blank screen
"No data"
raw stack trace
```

---

# 70. RESPONSIVENESS

Primary QA targets:

```text
1366×768
1440×900
1920×1080
```

Also test tablet width.

Lead tables may horizontally scroll at smaller widths, but the experience must remain usable.

---

# 71. ACCESSIBILITY

Implement:

```text
keyboard navigation
visible focus states
semantic HTML
accessible dialogs
accessible selectors
sufficient contrast
screen-reader labels
```

Use robust accessible primitives.

---

# 72. VISUAL QA LOOP

For EVERY major page:

```text
implement
→ run
→ visually inspect
→ capture screenshot if tooling permits
→ identify issues
→ fix
→ inspect again
```

Do not consider a page complete merely because it renders.

Required visual QA pages:

```text
Login
Overview
New Scan
Scan Preview
Live Campaign
Scans
Leads
Lead Detail
Reports
Settings
System
```

---

# 73. NO PLACEHOLDER PRODUCTION UI

Before completion remove:

```text
fake leads
fake stats
fake charts
Lorem ipsum
dead buttons
unfinished nav items
placeholder notifications
```

Everything visible must either work or clearly state why it is unavailable.

---

# 74. CLOUD ARCHITECTURE

Production target:

```text
Users
  ↓
Vercel
Next.js 16
  ↓
secure server-side BFF
  ↓
Google Cloud Run
FastAPI
  ↓
┌──────────────┬───────────────────────┐
│              │                       │
PostgreSQL     Cloud Run Job           R2
Neon           LeadEngine Worker       Artifacts
```

---

# 75. VERCEL

Deploy the Next.js dashboard to Vercel.

Do not attempt to execute the heavy crawler/Lighthouse pipeline inside a Vercel function.

Vercel hosts:

```text
Next.js UI
Auth
BFF/proxy routes
```

---

# 76. FASTAPI CLOUD DEPLOYMENT

Containerize FastAPI separately.

Deploy:

```text
leadengine-api
```

to:

```text
Google Cloud Run Service
```

FastAPI handles:

```text
authorized API calls
database operations
scan campaign creation
cloud-job launching
lead workflow
settings
reports
health
```

Do not execute Lighthouse inside the API service.

---

# 77. CLOUD WORKER

Containerize the existing LeadEngine execution environment.

Worker includes:

```text
Python 3.12+
Node 24 LTS
Chromium/Chrome
Lighthouse
required Python dependencies
LeadEngine core
```

Run as:

```text
Google Cloud Run Job
```

Default:

```text
one job execution per child pipeline run
```

or one campaign job if repository design shows a safer batching model.

Favor correctness and resumability over premature parallelization.

---

# 78. CLOUD RUN JOB LIMITS

Start conservatively.

Initial defaults:

```text
CLOUD_RUN_TASK_COUNT=1
CLOUD_RUN_PARALLELISM=1
```

Do NOT assume quota availability.

Before increasing:

```text
inspect actual regional quota
run canary worker
measure CPU/memory
```

Cloud Run permits long-running jobs, so use job execution rather than holding HTTP requests open.

---

# 79. GOOGLE CLOUD QUOTA PREFLIGHT

Before final cloud deployment create:

```text
docs/GCP_QUOTA_REPORT.md
```

Record:

```text
project
region
billing state
Cloud Run availability
regional CPU quota relevant to configuration
regional memory quota
job task parallelism availability
successful canary job result
```

Do not claim quota based on generic documentation.

Use the user's actual Google Cloud project.

If quota supports:

```text
1 task
1–2 vCPU
2–4 GiB
```

proceed.

Do not require GPU.

Do not use Vertex AI.

---

# 80. GCP QUOTA FAILURE

If the Free Trial account cannot execute even the minimum viable Cloud Run Job:

1. do not hack around it;
2. do not silently create expensive infrastructure;
3. keep `LocalScanExecutor` fully functional;
4. complete the hosted dashboard/API/database/storage work;
5. create:

```text
docs/GCP_QUOTA_BLOCKER.md
```

with exact error/quota details.

Azure is a contingency only.

Do NOT proactively build a second cloud stack.

Only implement Azure Container Apps Jobs if:

```text
GCP worker is demonstrably blocked
AND
Azure credentials/subscription are available
AND
the same ScanExecutor interface can be reused
```

---

# 81. EXECUTOR ABSTRACTION

Preserve:

```text
LocalScanExecutor
```

Add:

```text
CloudRunScanExecutor
```

Expose:

```text
SCAN_EXECUTOR=local
SCAN_EXECUTOR=gcp
```

Architecture should permit:

```text
auto
```

later.

Do not break local development.

---

# 82. WORKER IDEMPOTENCY

Cloud executions may retry.

Make worker operations safe for retries.

Use:

```text
run IDs
campaign IDs
database checkpoints
upserts
idempotent event writes where necessary
```

Do not create duplicate leads/exports because a Cloud Run task retries.

---

# 83. CLOUD RUN JOB RETRIES

Configure bounded retries.

Do not leave infinite application retries.

Failures should be classified:

```text
transient
permanent
cancelled
quota/resource
```

Use existing checkpoint/resume architecture.

---

# 84. WORKER CANCELLATION

Cloud scans must support cancellation.

User:

```text
Cancel Scan
```

Backend persists:

```text
cancellation_requested
```

Worker checks periodically between bounded units/stages.

Stop gracefully.

Preserve completed results.

---

# 85. POSTGRES-BACKED EVENTS

Cloud workers and API are separate processes.

Therefore live progress cannot rely on in-memory state.

Use Postgres:

```text
pipeline_run_events
```

Worker writes events.

FastAPI reads/streams events.

Next.js consumes them via the authenticated BFF.

Preserve polling fallback.

---

# 86. OBJECT STORAGE

Move generated artifacts out of local filesystem for production.

Use:

```text
Cloudflare R2
```

for:

```text
XLSX
CSV
HTML reports
Lighthouse JSON
future audit screenshots if added
```

Recommended keys:

```text
campaigns/{campaign_id}/runs/{run_id}/leads.xlsx

campaigns/{campaign_id}/runs/{run_id}/leads.csv

prospects/{prospect_id}/reports/{timestamp}.html

audits/{run_id}/{business_id}/lighthouse.json
```

---

# 87. R2 SECURITY

Bucket must remain private.

Use bucket-scoped credentials.

No public listing.

Downloads should use:

```text
authenticated proxy
or short-lived signed URL
```

Validate all object keys.

Do not accept arbitrary paths from clients.

---

# 88. CONTAINER SECURITY

Cloud images:

```text
minimal base
non-root user where compatible
no embedded credentials
no .env in image
no service-account JSON
bounded temporary storage
no privileged mode
resource limits
```

Preserve existing SSRF controls.

---

# 89. GCP SERVICE IDENTITIES

Use attached Google Cloud service accounts.

Expected identities:

```text
leadengine-api-sa

leadengine-worker-sa
```

Do NOT generate/download long-lived service-account JSON keys unless absolutely unavoidable.

Grant least privilege.

API identity needs only what is required to:

```text
invoke/run LeadEngine job
read required secrets
write logs
```

Worker identity needs only what it actually uses.

---

# 90. GOOGLE SECRET MANAGER

Production backend secrets may be stored in Google Secret Manager.

Do not bake them into containers.

Secrets include:

```text
DATABASE_URL
R2 credentials
internal API signing secret
```

Vercel-specific auth secrets remain in Vercel secrets as appropriate.

---

# 91. COST / RESOURCE PROTECTION

Hard application limits are mandatory.

Support configuration such as:

```text
MAX_ACTIVE_SCANS=2
MAX_CITIES_PER_SCAN=10
MAX_TARGET_LEADS=1000
MAX_RAW_BUSINESSES=10000
MAX_LIGHTHOUSE_AUDITS=500
MAX_SCAN_RUNTIME_MINUTES=180
```

Validate them server-side.

One UI click must not accidentally trigger:

```text
6 countries
× every city
× every vertical
× unlimited businesses
```

---

# 92. PRODUCTION SETTINGS

Settings UI must distinguish:

```text
normal scan settings
```

from:

```text
infrastructure safety limits
```

Do not expose dangerous cloud limits casually.

Critical infrastructure limits can be read-only in UI and changed through secure environment/deployment configuration.

---

# 93. OUTREACH GUIDANCE METADATA

Lead discovery is not the same as permission to send unsolicited email.

For preset countries, optionally display simple non-blocking informational guidance:

```text
United States
United Kingdom
Canada
Australia
France
Germany
```

Do not make legal guarantees.

Do not prevent discovery.

Do not implement outreach in Phase 3.

---

# 94. REPORTS & EXPORTS

Preserve:

```text
XLSX
CSV
HTML lead reports
```

Update them to include:

```text
website opportunity score
SEO opportunity score
security opportunity score
primary opportunity
secondary opportunity
business scale
contactability
lead status
assigned user
first seen
last seen
```

Do not destroy compatibility with historical exports unless necessary.

---

# 95. SYSTEM PAGE

Upgrade `/system` for hosted operation.

Show actual health:

```text
Dashboard
FastAPI
PostgreSQL
Cloud Worker Configuration
R2
Overture
OpenStreetMap
Nominatim
Lighthouse worker configuration
```

Never expose secret values.

---

# 96. CLOUD CANARY TEST

Create a minimal test command/action.

Example:

```text
python lead_engine.py cloud-doctor
```

Check:

```text
GCP auth/config
job exists
job executable
database reachable
R2 reachable
worker image reachable
canary worker completes
```

Do not run a large scan.

---

# 97. LOCAL EXPERIENCE MUST CONTINUE WORKING

Keep:

```powershell
python lead_engine.py ui
```

for local development.

Local mode:

```text
Next.js
FastAPI
SQLite or configured Postgres
LocalScanExecutor
```

Production mode:

```text
Vercel
Cloud Run API
Postgres
CloudRunScanExecutor
R2
```

---

# 98. VERCEL DEPLOYMENT

Prepare the dashboard for Vercel.

Ensure:

```text
Next.js 16 production build
Node 24
environment validation
no filesystem assumptions
no Python process assumptions
no direct localhost API assumptions
```

Configure:

```text
LEADENGINE_API_URL
```

server-side.

Do not expose it unnecessarily as `NEXT_PUBLIC_*`.

---

# 99. ENVIRONMENT VALIDATION

Create robust environment validation.

Next.js should validate required server env at startup/build where appropriate.

Python should use Pydantic Settings.

Differentiate:

```text
local
test
production
```

Missing production-critical variables should fail clearly.

Do not silently run production with unsafe defaults.

---

# 100. TESTING — EXISTING BASELINE

The following minimum baseline must remain green:

```text
31 Phase-2 Python tests

8 Phase-2 frontend tests

TypeScript strict

ESLint

Next production build
```

Do not reduce test count by deleting tests.

---

# 101. NEW PYTHON TESTS

Add comprehensive tests for:

```text
all new vertical validators

location presets

campaign expansion

canonical business identity

cross-run duplicate suppression

business-scale classification

website opportunity scoring

SEO opportunity scoring

security opportunity scoring

primary/secondary opportunity

contactability

workflow state

assignment

notes

Postgres repositories

SQLite compatibility where retained

internal API authentication

R2 storage abstraction

CloudRun executor contract

cloud cancellation state

event persistence
```

---

# 102. FRONTEND TESTS

Substantially expand beyond basic Button/Card/Badge tests.

Test real product flows:

```text
login protection

New Scan location selection

multi-city selection

multi-vertical selection

opportunity selection

lead quality

scan preview

lead score rendering

lead filters

workflow state

assignment

notes

loading states

empty states

error states
```

---

# 103. E2E

Add Playwright E2E for:

```text
authenticated test session

create campaign

choose multiple cities

choose multiple verticals

select Website + SEO + Security

start deterministic fixture campaign

watch progress

view leads

filter SEO opportunity

open lead

change status

assign lead

add note

generate report
```

Do not make CI depend on uncontrolled public websites.

Use deterministic fixture mode.

---

# 104. POSTGRES INTEGRATION TEST

Run database integration tests against actual PostgreSQL in development/test.

Do not claim Postgres compatibility based solely on SQLite tests.

---

# 105. SECURITY TESTS

Test:

```text
unauthenticated page access

unauthenticated scan creation

invalid API signature

expired API signature

replayed signed request

invalid pagination

invalid sort fields

path traversal attempts

private-IP crawler targets

metadata endpoint target

arbitrary export path

secret leakage

CORS behavior
```

---

# 106. PERFORMANCE

Do not load entire lead tables client-side.

Use:

```text
server pagination
server filters
server sorting
proper Postgres indexes
cached aggregates where useful
```

Inspect slow queries.

---

# 107. PRODUCTION DEPLOYMENT SCRIPTS

Create documented scripts/workflows for:

```text
database migration

FastAPI image build

worker image build

Artifact Registry push

Cloud Run API deploy

Cloud Run Job deploy

Vercel deployment/config
```

PowerShell-first documentation because development environment is Windows.

Do not require the user to reconstruct commands from memory.

---

# 108. DOCUMENTATION

Create:

```text
docs/PHASE_3_ARCHITECTURE.md

docs/PHASE_3_DEPLOYMENT.md

docs/PHASE_3_SECURITY.md

docs/GCP_QUOTA_REPORT.md

docs/PHASE_3_REPORT.md
```

Update README.

---

# 109. PHASE-3 FINAL REPORT

`docs/PHASE_3_REPORT.md` must include:

```text
baseline

dependency upgrades

Next.js migration

Node version

security hardening

new database architecture

migration results

new verticals

market presets

opportunity scoring

business-scale filtering

canonical lead identity

workflow/collaboration

authentication

premium UI work

FastAPI production architecture

Cloud Run API

Cloud Run worker

GCP quota findings

R2

Vercel

tests

E2E

security tests

live production smoke test

known limitations
```

Report exact test totals.

---

# 110. LIVE ACCEPTANCE SCAN

After deployment, perform a SMALL production smoke test.

Example:

```text
Country:
United States

City:
Austin

Vertical:
Home Services or Dentists

Opportunity:
Website + SEO + Security

Target:
5
```

Use conservative Cloud Run settings.

Verify:

```text
authenticated user creates campaign

FastAPI accepts request

Cloud Run worker starts

Postgres progress updates

dashboard receives progress

results appear

opportunity scores appear

lead status works

assignment works

notes work

export reaches R2

downloads work
```

---

# 111. TWO-USER ACCEPTANCE

Verify with both allowlisted accounts where possible:

```text
User A logs in

User A creates scan

User B logs in

User B sees same campaign

User B sees same leads

User A assigns lead to User B

User B sees assignment

User B updates status

User A sees updated status
```

This is a core Phase-3 requirement.

---

# 112. PREMIUM UI ACCEPTANCE

The phase is NOT complete merely because routes work.

Fail UI acceptance if:

```text
dashboard looks like a generic template

forms are overwhelming

tables are hard to scan

information hierarchy is weak

critical actions are hidden

dark mode is broken

common laptop widths overflow

loading states are poor

empty states are useless

errors are raw

pages feel visually inconsistent

placeholder data remains
```

---

# 113. TECHNOLOGY ACCEPTANCE

Do not mark complete unless:

```text
[ ] Next.js 14 removed
[ ] latest appropriate patched Next.js 16.x used
[ ] Node 24 LTS configured
[ ] React version officially supported
[ ] unsupported/deprecated Next APIs removed
[ ] TypeScript strict passes
[ ] production Next build passes
[ ] dependency vulnerability review complete
```

---

# 114. SECURITY ACCEPTANCE

Do not mark complete unless:

```text
[ ] auth required
[ ] Google email verified
[ ] email allowlist enforced server-side
[ ] no public signup
[ ] protected Next routes
[ ] protected FastAPI operations
[ ] signed internal API authentication
[ ] replay protection
[ ] CSP
[ ] HSTS
[ ] nosniff
[ ] referrer policy
[ ] permissions policy
[ ] clickjacking protection
[ ] secure cookies
[ ] no browser secrets
[ ] no service-account JSON
[ ] private R2
[ ] SSRF defenses preserved
[ ] production errors sanitized
```

---

# 115. CLOUD ACCEPTANCE

Do not mark complete unless:

```text
[ ] local executor preserved
[ ] CloudRunScanExecutor implemented
[ ] actual GCP quota inspected
[ ] quota report written
[ ] canary Cloud Run Job passes OR blocker documented
[ ] worker retries idempotent
[ ] cloud cancellation supported
[ ] Postgres progress persists
[ ] cloud execution does not depend on browser session
[ ] hard workload limits exist
```

---

# 116. PRODUCT ACCEPTANCE

Do not mark complete unless:

```text
[ ] seven target vertical families supported
[ ] country presets work
[ ] city multi-select works
[ ] custom location still works
[ ] multi-vertical scan works
[ ] campaign/child-run model works

[ ] website opportunity score works
[ ] SEO opportunity score works
[ ] passive security opportunity works
[ ] primary/secondary opportunity works

[ ] established players filter works
[ ] contactability works
[ ] new-lead suppression works

[ ] lead status works
[ ] assignment works
[ ] notes work

[ ] both users can use shared hosted data
```

---

# 117. DEVELOPMENT ORDER

Follow this order.

## Phase 3A

```text
Baseline audit
→ dependency audit
→ Next.js 16 migration
→ Node 24
→ framework/security hardening
→ baseline tests
```

## Phase 3B

```text
Postgres abstraction
→ schema migrations
→ SQLite migration tool
→ canonical prospect identity
→ users/workflow
```

## Phase 3C

```text
vertical expansion
→ country/city presets
→ campaign model
→ multi-city/multi-vertical scans
```

## Phase 3D

```text
shared crawl
→ website opportunity
→ SEO opportunity
→ security opportunity
→ business scale
→ contactability
```

## Phase 3E

```text
premium dashboard redesign
→ login
→ overview
→ new scan
→ campaign monitor
→ lead explorer
→ lead detail
→ workflow collaboration
```

## Phase 3F

```text
R2
→ containerization
→ Cloud Run API
→ Cloud Run worker
→ quota preflight
→ Vercel deployment
```

## Phase 3G

```text
backend tests
→ frontend tests
→ Postgres integration
→ E2E
→ security tests
→ visual QA
→ cloud smoke
→ two-user smoke
→ documentation
```

---

# 118. AUTONOMOUS EXECUTION RULE

Do NOT stop after scaffolding.

Do NOT stop after database migration.

Do NOT stop after UI creation.

Do NOT build mock screens disconnected from real data.

Do NOT ask me to wire ordinary configuration manually.

Use available credentials/environment variables securely.

If a credential required only for final deployment is missing:

```text
complete all implementation possible
create clear deployment blocker documentation
keep local mode working
```

Do not fabricate successful cloud deployment.

---

# 119. FINAL PRODUCT EXPERIENCE

The expected user flow:

```text
Google Login

        ↓

Premium Overview

        ↓

New Scan

        ↓

Choose:
United States

Miami
Dallas
Atlanta

        ↓

Choose:
Home Services
Dentists
Real Estate

        ↓

Analyze:
Website
SEO
Basic Security

        ↓

Balanced

        ↓

Start Scan

        ↓

Cloud worker processes campaign

        ↓

Live progress

        ↓

Qualified leads
```

Leads show:

```text
ABC Plumbing

Website        91
SEO            68
Security       42

Primary
WEBSITE

Contactability
HIGH

Status
NEW

Assigned
Unassigned
```

Another:

```text
Prime Dental

Website        22
SEO            89
Security       37

Primary
SEO

Contactability
HIGH
```

The founders can:

```text
Shortlist
Assign
Add Note
Mark Contacted
Mark Replied
Mark Won
```

without duplicate spreadsheets or local-only data.

That is the required Phase-3 end state.

START NOW.

First inspect the actual Phase-2 repository and reproduce its current passing baseline.

Then modernize the technology stack and security.

Do not begin feature expansion on Next.js 14.

Do not sacrifice existing working behavior.

Do not silently assume cloud quota.

Do not compromise the premium UI quality bar.

Complete Phase 3 end-to-end.