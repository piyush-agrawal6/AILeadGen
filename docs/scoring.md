# LeadEngine Lead Scoring & Qualification Model

LeadEngine uses an explainable, deterministic scoring system configured via `config/scoring.yaml`. The goal is to measure **sales opportunity**: the higher the score, the more acute the business's digital deficiencies and the more receptive they will be to web redesign, technical SEO, and conversion optimization services.

---

## 1. Score Normalization & Pillars

The total opportunity score is normalized on a **0 to 100** scale, calculated across 4 capped pillars:

| Pillar | Description | Maximum Points |
| :--- | :--- | :--- |
| **Website Opportunity** | Core technical, mobile, security, and performance gaps | **55 pts** |
| **SEO Opportunity** | Meta tags, heading structure, canonicals, schema.org | **20 pts** |
| **Vertical Opportunity** | Industry-specific friction (reservations, menus, booking) | **15 pts** |
| **Contactability** | Availability of public business contact channels | **10 pts** |
| **TOTAL** | **Normalized Combined Opportunity** | **100 pts** |

---

## 2. Pillar Weights & Findings Catalog

### Pillar 1: Website Opportunity (Cap: 55 pts)
- **No Website Found**: `+40 pts` *(Highest priority: urgent greenfield prospect)*
- **Website Unreachable / Domain Down**: `+35 pts`
- **Missing Mobile Viewport (`<meta name="viewport">`)**: `+20 pts`
- **Missing HTTPS Encryption**: `+15 pts`
- **Lighthouse Mobile Performance < 40**: `+20 pts`
- **Lighthouse Mobile Performance 40–59**: `+12 pts`
- **Lighthouse Mobile Performance 60–74**: `+5 pts`
- **No Dedicated Contact Page**: `+5 pts`
- **No High-Visibility CTA Button**: `+6 pts`
- **No Commonly Detectable Analytics Tag**: `+3 pts`

### Pillar 2: SEO Opportunity (Cap: 20 pts)
- **Lighthouse SEO Score < 50**: `+18 pts`
- **Lighthouse SEO Score 50–64**: `+12 pts`
- **Lighthouse SEO Score 65–79**: `+5 pts`
- **No JSON-LD Structured Data**: `+6 pts`
- **Missing Vertical-Specific Schema**: `+5 pts`
- **Missing HTML `<title>`**: `+5 pts`
- **Missing Meta Description**: `+4 pts`
- **Missing `<h1>` Heading**: `+3 pts`
- **Missing Canonical Tag**: `+2 pts`

### Pillar 3: Vertical-Specific Opportunity (Cap: 15 pts)

#### Restaurants & Bars
- **No Online Reservation Flow**: `+10 pts`
- **PDF-Only Menu Format**: `+8 pts`
- **No Online Ordering Integration**: `+5 pts`
- **Missing Schema.org/Restaurant**: `+5 pts`

#### Hotels & Hospitality
- **No Direct Booking Engine**: `+12 pts`
- **Weak Room Showcase / No Room Pages**: `+5 pts`
- **Missing Schema.org/Hotel or LodgingBusiness**: `+5 pts`

#### Real Estate Agencies
- **No Interactive Property / MLS Search**: `+10 pts`
- **Weak / Missing Lead Capture / Valuation Funnel**: `+8 pts`
- **No Dedicated Agent / Team Profiles**: `+4 pts`
- **Missing Schema.org/RealEstateAgent**: `+5 pts`

### Pillar 4: Contactability (Cap: 10 pts)
- **Valid Public Business Email (DNS verified)**: `+5 pts`
- **Published Telephone Number**: `+3 pts`
- **Public Contact Form**: `+2 pts`
- **Active Business Social Account**: `+2 pts`

---

## 3. Lead Tiers

| Tier | Score Range | Classification | Recommendation |
| :--- | :--- | :--- | :--- |
| **A+** | **80 – 100** | **Hot Leads** | Immediate high-touch personal outreach |
| **A** | **65 – 79** | **Strong Opportunities** | Primary sales target list |
| **B** | **50 – 64** | **Moderate Opportunities** | Secondary sales outreach |
| **C** | **35 – 49** | **Low Opportunity** | Minor technical improvements |
| **D** | **< 35** | **Not Recommended** | Well-optimized or modern stack |

---

## 4. Deterministic Service Recommendations

LeadEngine classifies the recommended pitch angle deterministically:

| Audit Signals | Recommended Service | Example Sales Angle |
| :--- | :--- | :--- |
| No website | `NEW WEBSITE + LOCAL SEO` | "Help launch an official mobile-friendly web presence to capture local customer demand." |
| No viewport + very slow | `WEBSITE REDESIGN + PERFORMANCE OPTIMIZATION` | "Redesign layout for responsive smartphone screens to stop losing mobile prospects." |
| Restaurant with PDF menu | `RESERVATION UX + LOCAL SEO` | "Convert mobile-unfriendly PDF menu into an SEO-indexed digital menu to boost Google discovery." |
| Hotel with no booking engine | `BOOKING UX + WEBSITE REDESIGN` | "Implement a direct booking engine to eliminate costly OTA commissions and increase reservations." |
| Real estate with no property search | `WEBSITE REDESIGN + MLS SEARCH INTEGRATION` | "Integrate an interactive property search filter to keep local home seekers on the site." |
| Fast site with weak metadata | `TECHNICAL SEO + LOCAL SEO` | "Implement Schema.org rich snippets and metadata to enhance Google Maps and search CTR." |
