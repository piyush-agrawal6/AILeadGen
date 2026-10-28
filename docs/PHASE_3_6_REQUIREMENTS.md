# LEADENGINE PHASE 3.6
# SOCIAL INTELLIGENCE + MID-MARKET TARGETING + SALES-OPTIMIZED CLIENT REPORTS

You are Astra acting as the senior principal engineer, data-enrichment engineer, product architect, frontend engineer, crawling/security engineer, PDF/report designer, and QA owner for the existing LeadEngine repository.

Phase 3 and Phase 3.5 are COMPLETE and production accepted.

DO NOT rebuild the application.

DO NOT replace working infrastructure.

DO NOT rewrite:

- authentication;
- Vercel deployment;
- FastAPI architecture;
- PostgreSQL;
- R2;
- Cloud Run worker architecture;
- opportunity scoring;
- client-report versioning;
- existing lead workflow;
- campaign architecture.

This is a focused Phase 3.6 improvement.

---

# 1. PHASE GOAL

Improve LeadEngine in three areas:

```text
1. Social presence intelligence

2. Better targeting of businesses that
   can realistically afford PlaneByte services

3. More compelling and sales-effective
   client-facing PlaneByte PDF reports
```

The product should move from:

```text
Find businesses with digital problems
```

toward:

```text
Find commercially attractive businesses
with measurable digital problems,
understand their wider online presence,
and present those problems in a
professional way that creates urgency.
```

Do NOT add outreach automation yet.

Phase 4 remains separate.

---

# 2. CURRENT ACCEPTED BASELINE

Preserve the current Phase 3.5 baseline.

At Phase 3.5 completion:

```text
Python tests       118 passed
Frontend tests      35 passed
Browser tests        6 passed

TypeScript strict    PASS
ESLint               PASS
Production build     PASS

Dependency audits:
0 known vulnerabilities
```

Current production architecture:

```text
Vercel
Next.js 16
        ↓
authenticated BFF
        ↓
Cloud Run FastAPI
        ↓
PostgreSQL / Neon
        ↓
Cloud Run worker
        ↓
R2 private storage
```

Current PDF architecture is already:

```text
immutable report snapshot
→ versioned client_reports
→ PDF rendering
→ private R2 object
→ authenticated download
```

EXTEND this.

Do not create another reporting subsystem.

---

# 3. PHASE 3.6 SCOPE

Implement:

```text
A. Social profile discovery

B. Public social activity intelligence

C. Social presence UI

D. Business-scale classifier improvement

E. MID_MARKET business class

F. Better commercial targeting

G. Scan business-size selector update

H. Commercial-fit prioritization

I. Stronger client-facing PDF visual hierarchy

J. Website screenshot/evidence in PDF

K. Stronger business-impact explanations

L. Recommended action plan

M. PlaneByte value-stack / included-services offer

N. Production QA and regression verification
```

Do NOT implement:

```text
automatic social posting

social login using prospect accounts

social DMs

automatic emails

Gmail integration

AI-written outreach

bulk outreach

paid enrichment APIs

employee scraping

private social data

login bypass

CAPTCHA bypass

social-platform anti-bot bypass
```

---

# PART A
# SOCIAL PROFILE DISCOVERY

# 4. SOCIAL PLATFORMS

Initially support:

```text
Instagram
Facebook
LinkedIn
X / Twitter
YouTube
TikTok
Pinterest
Threads
```

Do not assume every vertical needs every platform.

---

# 5. SOCIAL PROFILE SOURCES

Discover social profiles from existing public evidence.

Priority order:

```text
1. Website JSON-LD sameAs

2. Website footer/header/social icons

3. Contact page

4. About page

5. Website HTML links

6. Overture source fields where available

7. OSM social tags where available

8. Other already-ingested public source metadata
```

Do NOT introduce Google/Bing scraping just to find social profiles.

Do NOT scrape search-result pages.

---

# 6. WEBSITE SOCIAL DISCOVERY

Enhance the existing shared crawl.

Inspect:

```text
a[href]
JSON-LD sameAs
OpenGraph/profile metadata
contact/about/footer elements
```

Normalize links.

Recognize canonical social domains.

Examples:

```text
instagram.com
facebook.com
fb.com
linkedin.com
x.com
twitter.com
youtube.com
youtu.be
tiktok.com
pinterest.com
threads.net
```

---

# 7. DO NOT CONFUSE SHARE LINKS WITH PROFILES

Reject URLs such as:

```text
facebook.com/sharer
twitter.com/intent
x.com/intent
linkedin.com/shareArticle
pinterest.com/pin/create
youtube.com/watch
```

when determining business social profiles.

Also reject:

```text
login URLs
tracking URLs
generic platform home pages
support/help pages
```

---

# 8. SOCIAL PROFILE VALIDATION

Each discovered social profile should have:

```text
platform
url
handle if derivable
source
source_url
confidence
discovered_at
last_checked_at
```

Suggested confidence:

```text
HIGH
MEDIUM
LOW
```

Examples:

```text
JSON-LD sameAs
→ HIGH

business website footer
→ HIGH

OSM social tag
→ MEDIUM/HIGH

ambiguous source
→ LOW
```

Do not invent handles.

---

# 9. NEW DATA MODEL

Introduce a structure such as:

```text
social_profiles

id
canonical_prospect_id
platform
profile_url
handle
source_type
source_url
confidence
last_activity_at
activity_status
activity_source
activity_evidence_url
activity_checked_at
metadata_json
created_at
updated_at
```

Adapt naming to existing repository conventions.

Add appropriate uniqueness/index constraints.

---

# PART B
# SOCIAL ACTIVITY

# 10. GOAL

We want to know:

```text
Does the prospect appear to maintain
an active public social presence?
```

NOT:

```text
How many followers can we scrape?
```

Do not make follower count the primary objective.

---

# 11. SOCIAL ACTIVITY STATES

Use:

```text
RECENT

ACTIVE

STALE

UNKNOWN
```

Suggested deterministic thresholds:

```text
RECENT
last reliable public activity <= 30 days

ACTIVE
31–90 days

STALE
>90 days

UNKNOWN
no reliable timestamp available
```

Make thresholds configurable.

Example env/config:

```text
SOCIAL_ACTIVITY_RECENT_DAYS=30
SOCIAL_ACTIVITY_ACTIVE_DAYS=90
```

---

# 12. CRITICAL RULE

Never infer:

```text
STALE
```

merely because automated access failed.

If the platform blocks access:

```text
activity_status = UNKNOWN
```

not:

```text
STALE
```

---

# 13. PUBLIC DATA ONLY

Activity detection may use:

```text
public machine-readable metadata

public profile pages where access
is permitted and technically available

public post timestamps exposed without login

official APIs when credentials and
permissions legitimately allow it
```

Do NOT:

```text
log in with fake accounts

reuse user cookies

bypass login walls

solve CAPTCHA

use residential proxy networks

circumvent anti-bot systems

reverse-engineer private endpoints
```

---

# 14. PLATFORM-SPECIFIC BEHAVIOR

The implementation must acknowledge platform limitations.

## LinkedIn

Profile URL discovery:

```text
YES
```

Arbitrary company recent-post retrieval:

```text
DO NOT assume available
```

If no legitimate API/public evidence exists:

```text
activity_status = UNKNOWN
```

## Facebook

Profile/Page URL discovery:

```text
YES
```

Activity:

best-effort public evidence only.

If approved Page-public API access is unavailable:

```text
UNKNOWN
```

is acceptable.

## Instagram

Discover business/creator profile URLs.

Best-effort public activity only.

Do not assume access to arbitrary account media.

## X

Create an adapter interface capable of using an official X API token later.

Do not require an X key for this phase.

Without legitimate API/public timestamp evidence:

```text
UNKNOWN
```

## YouTube

Public channel/activity timestamps may be assessed only through legitimately accessible public data.

## TikTok / Pinterest / Threads

Profile discovery first.

Activity is optional/best-effort.

---

# 15. SOCIAL ACTIVITY ADAPTER ARCHITECTURE

Create:

```text
SocialActivityProvider
```

interface.

Example:

```text
check(profile) -> SocialActivityResult
```

Result:

```text
status
last_activity_at
source
evidence_url
confidence
reason
```

Implement:

```text
PublicWebSocialActivityProvider
```

for legitimately accessible public evidence.

Leave clean extension points for:

```text
MetaProvider
XProvider
```

later.

Do not require new paid API credentials now.

---

# 16. BOUNDED SOCIAL REQUESTS

Social enrichment must be bounded.

Example:

```text
SOCIAL_PROFILE_MAX_REQUESTS_PER_BUSINESS=4
SOCIAL_PROFILE_TIMEOUT_SECONDS=8
SOCIAL_ACTIVITY_CONCURRENCY=2
```

Do not significantly slow normal campaigns.

---

# 17. OPTIONAL SOCIAL ACTIVITY MODE

Add campaign configuration:

```text
Social enrichment

☑ Discover social profiles

☑ Check recent public activity
```

Default:

```text
Discover profiles = true
Activity check = true
```

but use bounded execution.

---

# 18. SOCIAL DATA UI — LEAD TABLE

Do NOT add eight new columns.

Under the Business/contact area show compact icons:

```text
Instagram
Facebook
LinkedIn
X
```

only when discovered.

Example:

```text
Ditton Lodge
dittonlodge.co.uk
☎ +44...
✉ hello@...

IG   FB   LI
```

Hover/tooltip:

```text
Instagram
Recently active
Last verified activity: 12 days ago
```

or:

```text
LinkedIn
Profile found
Activity unknown
```

---

# 19. SOCIAL DATA UI — LEAD DETAIL

Create:

```text
Social presence
```

section.

Example:

```text
Instagram

@dittonlodge
RECENT
Last public activity observed:
12 days ago

[ Open profile ]
```

```text
Facebook

facebook.com/dittonlodge
ACTIVE
Last public activity observed:
43 days ago
```

```text
LinkedIn

linkedin.com/company/...
UNKNOWN
Recent activity could not be reliably verified.
```

Do not make UNKNOWN look like an error.

---

# 20. SOCIAL PRESENCE SUMMARY

Calculate a lightweight:

```text
social_presence_status
```

Example values:

```text
ACTIVE
PARTIAL
STALE
NONE
UNKNOWN
```

Do NOT turn this into another 0–100 sales score yet.

---

# 21. SOCIAL FINDINGS

Useful deterministic findings may include:

```text
NO_SOCIAL_PROFILES_FOUND

SOCIAL_PROFILES_PRESENT

SOCIAL_ACTIVITY_RECENT

SOCIAL_ACTIVITY_STALE
```

Only generate `SOCIAL_ACTIVITY_STALE` from reliable timestamp evidence.

---

# 22. DO NOT PENALIZE ALL BUSINESSES WITHOUT SOCIAL MEDIA

Social presence importance differs by vertical.

Example:

More relevant:

```text
Hotels
Hospitality
Real Estate
Dentists
Veterinary
```

Potentially less essential:

```text
some B2B legal
some contractors
some property management
```

Social presence is context, not an automatic rejection criterion.

---

# PART C
# BUSINESS SCALE / MID-MARKET

# 23. CURRENT PROBLEM

LeadEngine currently over-selects very small businesses.

That creates leads that may have strong needs but limited budgets.

We now want to target:

```text
small businesses
+
mid-sized businesses
```

while continuing to avoid:

```text
large enterprise
national/international chains
```

---

# 24. NEW SCALE MODEL

Use:

```text
LOCAL

SMALL_GROUP

MID_MARKET

REGIONAL

ENTERPRISE

KNOWN_CHAIN
```

MID_MARKET is new and important.

---

# 25. SUGGESTED LOCATION FOOTPRINT SIGNALS

Do not classify only by location count.

However, use location count as one signal.

Initial heuristic:

```text
LOCAL
1 location

SMALL_GROUP
2–5 locations

MID_MARKET
6–25 locations

REGIONAL
26–100 locations

ENTERPRISE
100+ locations
```

These are heuristic bands, NOT absolute truth.

They must be combined with other signals.

---

# 26. ADDITIONAL SCALE SIGNALS

Use evidence such as:

```text
same domain across locations

same normalized brand across locations

number of cities

number of states/regions

location directory on website

number of office/location pages

corporate/about structure

multi-location schema

franchise indicators

known-chain list

brand footprint in Overture/OSM

website complexity
```

Do NOT estimate:

```text
revenue
profit
employee count
```

without real evidence.

---

# 27. VERTICAL-SENSITIVE SCALE CLASSIFICATION

A 15-location dental group may be a fantastic target.

A 15-location hotel group may also be attractive.

Do not reject them merely because they are larger than a local shop.

Design the classifier to support vertical-specific context.

Example:

```text
15-location dental group
→ MID_MARKET
→ strong target
```

not:

```text
CHAIN
→ reject
```

unless actual franchise/large-chain evidence exists.

---

# 28. MID-MARKET TARGETING

Default targeting for new scans should become:

```text
☑ Local
☑ Small Group
☑ Mid-Market
☐ Regional
☐ Enterprise
☐ Known Chains
```

This is important.

Previously MID_MARKET effectively did not exist.

---

# 29. OPTIONAL REGIONAL TARGETING

Allow:

```text
☑ Regional
```

for users who want larger opportunities.

Keep:

```text
Enterprise
Known Chain
```

disabled by default.

---

# 30. COMMERCIAL FIT

Introduce:

```text
commercial_fit
```

as:

```text
HIGH
MEDIUM
LOW
UNKNOWN
```

Do NOT create a fake revenue score.

Commercial fit should use transparent public proxies such as:

```text
business scale

multi-location footprint

website existence

professional domain

public contactability

vertical

digital sophistication

business continuity signals
```

---

# 31. COMMERCIAL FIT IS NOT OPPORTUNITY SCORE

Example:

```text
Website Opportunity
92

Commercial Fit
LOW
```

could mean:

```text
terrible/no website
but extremely tiny prospect
```

Whereas:

```text
Website Opportunity
76

Commercial Fit
HIGH
```

may be more commercially attractive.

This distinction is valuable.

---

# 32. LEAD PRIORITIZATION

Lead table should optionally display:

```text
Commercial Fit
```

Use a compact indicator:

```text
HIGH
MEDIUM
LOW
```

Do not overwhelm the table.

Consider placing it beside:

```text
Contactability
```

or under Primary Opportunity.

---

# 33. LEAD FILTERS

Add:

```text
Business Size

Commercial Fit
```

values.

Example:

```text
Business Size
☑ Small Group
☑ Mid-Market

Commercial Fit
HIGH
```

---

# 34. NEW SCAN

Business-size selector becomes:

```text
Target business size

☑ Local
☑ Small Group
☑ Mid-Market
☐ Regional
```

Below:

```text
Enterprise and known national/international
chains are excluded by default.
```

---

# 35. QUALITY PRESETS

Adjust existing presets.

## Maximum Volume

```text
Local
Small Group
Mid-Market
Regional optional
```

## Balanced

```text
Small Group
Mid-Market
Local with strong evidence
```

## High Intent

Prefer:

```text
MID_MARKET
SMALL_GROUP
strong opportunity
good contactability
```

but do NOT automatically exclude a great local business.

---

# 36. DO NOT DESTROY CURRENT LEADS

Do not reclassify production history destructively.

If business-scale rules change:

```text
version the classification
```

or recalculate safely from stored evidence.

Do not delete existing business identities.

---

# PART D
# CLIENT PDF — SALES-OPTIMIZED V2

# 37. GOAL

The Phase 3.5 PDF is technically correct and professional.

Phase 3.6 should make it more:

```text
visually compelling

specific

evidence-heavy

persuasive

valuable

action-oriented
```

while remaining:

```text
truthful
professional
non-manipulative
client-safe
```

---

# 38. PDF SHOULD CREATE THIS REACTION

The reader should understand:

```text
1. Something important is underperforming.

2. The evidence is real.

3. It may affect their ability to
   attract/convert customers.

4. PlaneByte understands the problem.

5. PlaneByte has a clear plan to fix it.

6. The engagement includes additional value.
```

---

# 39. DO NOT USE FEAR-BASED SALES

Avoid language such as:

```text
YOUR WEBSITE IS LOSING THOUSANDS

YOUR BUSINESS IS AT RISK

HACKERS CAN ATTACK YOU

YOU ARE LOSING CUSTOMERS EVERY DAY
```

unless evidence proves the specific claim.

Use:

```text
This may reduce...
This can make...
This creates unnecessary friction...
This limits...
This leaves room for improvement...
```

---

# 40. ADD CURRENT DIGITAL PRESENCE PAGE

For reachable websites, capture a current screenshot during scanning.

Prefer:

```text
desktop above-the-fold screenshot
```

Optionally:

```text
mobile screenshot
```

if cheap enough.

Store screenshot privately in R2.

Suggested key:

```text
audits/{run_id}/{business_id}/website-desktop.webp
```

Use existing Playwright/Chromium environment.

---

# 41. SCREENSHOT SAFETY

Screenshot only:

```text
public business website
```

Do not capture:

```text
login pages
private dashboards
user-specific data
```

Use bounded page load.

---

# 42. PDF — CURRENT PRESENCE

Add page/section:

```text
Your Current Digital Presence
```

Include screenshot.

Beside/below it show:

```text
What we observed
```

with 3–5 strongest findings.

Example:

```text
⚠ Main conversion action is difficult to find

⚠ Mobile performance needs improvement

⚠ Important local SEO signals are missing

✓ HTTPS is configured
```

---

# 43. VISUAL SEVERITY SYSTEM

Use:

```text
CRITICAL
HIGH
MEDIUM
LOW
POSITIVE
```

with restrained colors.

Do not make every finding red.

---

# 44. FINDING FORMAT

Every important PDF finding should follow:

```text
Finding

Evidence

Why it matters

What we recommend
```

This structure is mandatory.

---

# 45. EXAMPLE

```text
MISSING LOCAL BUSINESS STRUCTURED DATA

What we found

No relevant LocalBusiness/Dentist schema
was detected on the sampled pages.

Why it matters

Structured data helps search engines
understand key business information.

What we recommend

Implement validated structured data for
the business, services and location.
```

---

# 46. ADD "TOP 3 OPPORTUNITIES"

Near the start of the report include:

```text
The 3 biggest opportunities
```

Example:

```text
01
Improve enquiry conversion

02
Strengthen local search foundations

03
Harden basic website security
```

Make it highly visual.

---

# 47. ADD OPPORTUNITY PRIORITY

For each:

```text
Impact
HIGH

Effort
MEDIUM
```

Do not fabricate exact ROI.

---

# 48. ADD BUSINESS IMPACT

Translate findings into business language.

Possible categories:

```text
Customer trust

Search visibility

Lead generation

Booking / enquiry conversion

Mobile experience

Brand perception

Website reliability
```

Only show categories supported by evidence.

---

# 49. ADD "WHAT HAPPENS IF WE FIX THIS"

Use qualitative outcome framing.

Example:

```text
A clearer mobile booking experience can
reduce friction between discovery and enquiry.
```

```text
A stronger local SEO foundation can make the
site easier for search engines to understand
for relevant locations and services.
```

Do NOT promise ranking or revenue.

---

# 50. ADD IMPLEMENTATION ROADMAP

Add:

```text
Recommended Plan
```

Example:

```text
PHASE 1
Foundation

Website architecture
UX
mobile
technical setup


PHASE 2
Visibility

technical SEO
local SEO
structured data


PHASE 3
Protection & launch

security hardening
performance
QA
monitoring
```

Use only relevant phases.

---

# 51. ADD "WHAT PLANEBYTE WILL DELIVER"

Instead of vague service names:

```text
Website redesign
```

show tangible deliverables:

```text
Responsive website

Conversion-focused page structure

Contact/enquiry experience

Technical SEO foundation

Analytics setup

Basic security hardening

Performance optimization

Launch QA
```

Only promise deliverables PlaneByte actually intends to provide.

---

# 52. VALUE STACK

Add a premium section:

```text
Included with your engagement
```

This should increase perceived value without deceptive pricing.

Suggested default for Website Redesign prospects:

```text
Website Strategy & UX Review
INCLUDED

Technical SEO Foundation
INCLUDED

Basic Security Hardening Review
INCLUDED

Post-launch Performance Audit
INCLUDED
```

---

# 53. WEBSITE PROJECT OFFER

Support a configurable PlaneByte offer.

Example:

```text
Website Redesign Offer

When PlaneByte designs and develops
your new website:

✓ Technical SEO foundation included

✓ Basic cybersecurity hardening included

✓ Post-launch technical audit included
```

Use wording:

```text
Included at no additional charge
```

rather than:

```text
FREE!!!
```

to maintain premium positioning.

---

# 54. OFFER CONFIGURATION

Do NOT hardcode the business offer in rendering logic.

Add config:

```text
REPORT_OFFER_ENABLED=true

REPORT_OFFER_TITLE=
Website Redesign Launch Package

REPORT_OFFER_SUBTITLE=
Included at no additional charge with an eligible PlaneByte website project.

REPORT_OFFER_INCLUDE_SEO_FOUNDATION=true

REPORT_OFFER_INCLUDE_SECURITY_HARDENING=true

REPORT_OFFER_INCLUDE_POST_LAUNCH_AUDIT=true
```

Adapt structure as needed.

---

# 55. NO FAKE VALUE NUMBERS

Do NOT show:

```text
SEO worth £2,000
FREE

Security worth £1,500
FREE
```

unless those are actual PlaneByte standalone prices.

If real values are configured later, support:

```text
configured list price
```

but never generate artificial anchors.

---

# 56. OPTIONAL REAL VALUE CONFIG

Support future:

```text
REPORT_SHOW_VALUE_STACK_PRICES=false
```

If true:

values must come from explicit PlaneByte configuration.

Never calculate them automatically.

---

# 57. CLIENT REPORT CTA

Strengthen final page.

Example:

```text
Your digital presence has clear room
for improvement — and the fixes are practical.

PlaneByte can handle the website,
technical SEO foundation and basic security
as one coordinated engagement.
```

Then:

```text
Discuss this audit with PlaneByte
```

Include:

```text
website
email
phone if configured
```

---

# 58. SOCIAL PRESENCE IN PDF

Add a concise:

```text
Social Presence
```

section only when useful.

Example:

```text
Instagram
RECENT

Facebook
ACTIVE

LinkedIn
Profile found — activity unverified
```

Do not turn the client report into a social analytics report.

---

# 59. SOCIAL OPPORTUNITY LANGUAGE

Example:

```text
Your Instagram account appears active,
which is a positive signal.

However, the website does not clearly connect
this audience to the booking/enquiry journey.
```

Only if supported by evidence.

---

# 60. MID-MARKET PDF TONE

For larger prospects:

avoid small-business language such as:

```text
You need a basic website.
```

Use:

```text
Modernization
Conversion optimization
Technical consolidation
Local visibility
Performance
Security hardening
```

Reports should feel credible for businesses with:

```text
multiple locations
teams
professional operations
```

---

# PART E
# UI REFINEMENTS

# 61. LEAD WORKSPACE

Business row may now show:

```text
Ditton Lodge

dittonlodge.co.uk

☎ phone
✉ email

IG  FB  LI
```

Do not increase row height excessively.

---

# 62. SOCIAL TOOLTIP

Example:

```text
Instagram

@dittonlodge

Recent public activity:
12 days ago
```

or:

```text
LinkedIn

Profile found

Recent activity:
Not reliably available
```

---

# 63. LEAD DETAIL

Add social section near:

```text
Public contact
```

or Business Information.

Do not bury it under technical evidence.

---

# 64. BUSINESS SCALE DISPLAY

Lead Detail:

```text
Business size
MID-MARKET
```

with explanation available:

```text
Multi-location business footprint
detected across 11 locations.
```

Do not expose internal classifier debugging unless expanded.

---

# 65. COMMERCIAL FIT DISPLAY

Use:

```text
Commercial fit
HIGH
```

with tooltip:

```text
Based on public business-scale,
contactability and digital-footprint signals.
```

Never imply financial certainty.

---

# PART F
# SCORING / PRIORITIZATION

# 66. DO NOT CHANGE EXISTING OPPORTUNITY MEANING

Preserve:

```text
Website Opportunity
SEO Opportunity
Security Opportunity
```

Do not mix social activity or size directly into those scores.

---

# 67. ADD COMMERCIAL FIT SEPARATELY

Example:

```text
Website Opportunity   82

Commercial Fit        HIGH
```

This allows:

```text
large need
+
realistic buyer
```

to rise naturally.

---

# 68. SORTING

Allow optional sorting by:

```text
Commercial Fit
```

Suggested ordering:

```text
HIGH
MEDIUM
LOW
UNKNOWN
```

Do not make it the default until validated.

---

# PART G
# TESTING

# 69. SOCIAL DISCOVERY TESTS

Test:

```text
JSON-LD sameAs

footer profiles

contact-page profiles

share-link rejection

duplicate normalization

platform normalization

invalid URLs

source confidence
```

---

# 70. ACTIVITY TESTS

Fixtures:

```text
recent public timestamp

60-day timestamp

180-day timestamp

blocked page

login wall

missing timestamp

timeout
```

Expected:

```text
RECENT
ACTIVE
STALE
UNKNOWN
UNKNOWN
UNKNOWN
UNKNOWN
```

respectively where appropriate.

---

# 71. NO FALSE STALE TEST

Explicit regression:

```text
HTTP 403 / blocked access
```

MUST NOT produce:

```text
STALE
```

It must produce:

```text
UNKNOWN
```

---

# 72. BUSINESS SCALE TESTS

Create fixtures for:

```text
single-location local business

3-location group

12-location dental group

45-location regional business

300-location national chain

known franchise
```

Verify:

```text
LOCAL

SMALL_GROUP

MID_MARKET

REGIONAL

ENTERPRISE

KNOWN_CHAIN
```

with reasonable confidence.

---

# 73. MID-MARKET ACCEPTANCE

Verify a multi-location legitimate business is NOT automatically rejected.

This is a critical regression.

---

# 74. PDF TESTS

Test:

```text
website screenshot included when available

no fabricated screenshot

top 3 opportunities

finding/evidence/impact/recommendation

implementation roadmap

PlaneByte offer section

included-services block

social presence section

no unsupported claims

no fake price anchors
```

---

# 75. PDF VARIANTS

Generate and visually inspect:

```text
1. Reachable small business

2. Reachable mid-market business

3. No website

4. Unreachable website
```

The mid-market report must not look like a generic small-business template.

---

# 76. PDF VISUAL QA

Rasterize every page.

Inspect:

```text
empty space

text density

page balance

screenshots

callouts

hierarchy

long URLs

long business names

offer block

CTA

footers

page numbering
```

The PDF should feel visually full but never cluttered.

---

# 77. NO FAKE CONTENT

Never invent:

```text
business images

social activity

employees

revenue

traffic

rankings

competitor metrics

pricing

savings

ROI
```

---

# PART H
# PRODUCTION ACCEPTANCE

# 78. SMALL LIVE ACCEPTANCE CAMPAIGN

After implementation run a controlled campaign.

Suggested:

```text
United Kingdom

London

Hospitality
or
Dentists

Target:
10

Sizes:
Small Group
Mid-Market

Analyzers:
Website
SEO
Security

Social enrichment:
enabled
```

---

# 79. ACCEPTANCE GOALS

Verify:

```text
social profiles discovered where public evidence exists

no fabricated profiles

activity statuses use evidence

blocked profiles are UNKNOWN

MID_MARKET prospects survive qualification

enterprise/known chains remain excluded

commercial-fit classification works

PDF screenshot works

PDF value-stack works

offer appears correctly

private R2 downloads work
```

Do NOT require every prospect to have social profiles.

---

# 80. PERFORMANCE CHECK

Measure additional social-enrichment overhead.

Report:

```text
average requests/business

average social enrichment time

activity success rate

UNKNOWN rate

campaign runtime change
```

If social checks significantly hurt throughput:

make activity checking optional/deferred.

---

# 81. SECURITY

Preserve:

```text
SSRF protection

private-IP rejection

metadata endpoint blocking

bounded redirects

response-size limits

timeouts

user agent

robots/TOS-aware public crawling
```

Social enrichment does not weaken crawler security.

---

# 82. DOCUMENTATION

Create:

```text
docs/PHASE_3_6_REPORT.md

docs/SOCIAL_ENRICHMENT.md

docs/BUSINESS_SCALE_V2.md

docs/CLIENT_REPORT_V2.md
```

---

# 83. ENV EXAMPLE

Document:

```text
SOCIAL_ENRICHMENT_ENABLED=true

SOCIAL_ACTIVITY_ENABLED=true

SOCIAL_ACTIVITY_RECENT_DAYS=30

SOCIAL_ACTIVITY_ACTIVE_DAYS=90

SOCIAL_ACTIVITY_CONCURRENCY=2

SOCIAL_PROFILE_TIMEOUT_SECONDS=8

REPORT_OFFER_ENABLED=true

REPORT_OFFER_TITLE=Website Redesign Launch Package

REPORT_OFFER_SUBTITLE=Included at no additional charge with an eligible PlaneByte website project.

REPORT_OFFER_INCLUDE_SEO_FOUNDATION=true

REPORT_OFFER_INCLUDE_SECURITY_HARDENING=true

REPORT_OFFER_INCLUDE_POST_LAUNCH_AUDIT=true

REPORT_SHOW_VALUE_STACK_PRICES=false
```

No new social API key is mandatory in Phase 3.6.

---

# 84. FINAL ACCEPTANCE CHECKLIST

Do not mark complete unless:

```text
[ ] Social profiles discovered from website/source evidence

[ ] social links normalized

[ ] share/login links excluded

[ ] social activity model implemented

[ ] RECENT/ACTIVE/STALE/UNKNOWN works

[ ] access failure never becomes STALE

[ ] no login/CAPTCHA bypass

[ ] MID_MARKET business class implemented

[ ] mid-sized prospects included by default

[ ] enterprise/known chains still excluded

[ ] commercial-fit classification implemented

[ ] filters updated

[ ] new scan business-size selection updated

[ ] website screenshots captured where available

[ ] PDF V2 uses stronger evidence presentation

[ ] top opportunities section added

[ ] business-impact section improved

[ ] implementation roadmap added

[ ] PlaneByte deliverables section added

[ ] Included-at-no-additional-charge offer added

[ ] offer configuration is not hardcoded

[ ] no fake price/value anchors

[ ] no unsupported claims

[ ] social presence appears appropriately in PDF

[ ] mid-market PDF tone verified

[ ] R2 remains private

[ ] all previous tests pass

[ ] new tests pass

[ ] TypeScript strict passes

[ ] ESLint passes

[ ] production build passes

[ ] production smoke campaign passes
```

---

# 85. IMPLEMENTATION ORDER

Follow:

```text
1. Baseline regression

2. Social-profile data model

3. Social discovery

4. Activity evidence abstraction

5. Social UI

6. Scale classifier V2

7. MID_MARKET targeting

8. Commercial-fit classification

9. Scan/filter UI updates

10. Website screenshot capture

11. PDF V2 structure

12. PDF business-impact rewrite

13. PlaneByte value stack

14. Configurable website-project offer

15. PDF visual QA

16. Automated regression

17. Controlled production campaign

18. Production verification

19. Phase 3.6 report
```

---

# FINAL PRODUCT PRINCIPLE

Phase 3.6 should improve LeadEngine from:

```text
"Here is a small business with a weak website."
```

to:

```text
"Here is a commercially attractive business.

We know its digital weaknesses.

We understand its broader online presence.

We have evidence.

We can explain the business impact.

And we can present a credible, valuable
PlaneByte plan to fix it."
```

Do not add unnecessary complexity.

Do not add Phase 4 outreach.

Do not sacrifice evidence quality for more data.

START NOW.