# LeadEngine Data Sources

LeadEngine operates exclusively on open, public, and non-commercial data sources with zero API keys or monthly subscription fees.

---

## 1. Overture Maps Foundation (Places Theme)

### Overview
Overture Maps Foundation provides open, high-quality map datasets released under the CDLA Permissive v2.0 license. The `places` theme contains hundreds of millions of public business records worldwide.

### Data Format & Access
- **Format**: Cloud-optimized GeoParquet.
- **Location**: AWS S3 (`s3://overturemaps-us-west-2/release/<release>/theme=places/type=place/*`).
- **Query Engine**: DuckDB with the `httpfs` extension.
- **Authentication**: Anonymous access (no AWS credentials required).

### Extracted Attributes
- `names['primary']`: Business trade name.
- `basic_category` / `taxonomy['primary']`: Category classification.
- `websites`: List of published official websites.
- `emails`: List of publicly listed business email addresses.
- `phones`: Published telephone numbers.
- `socials`: Official social media handles.
- `addresses[1]`: Structured physical address (street, city, state, postal code).
- `bbox`: Spatial bounds (`xmin`, `ymin`, `xmax`, `ymax`).
- `confidence`: Confidence score (0.0 to 1.0) of listing validity.
- `operating_status`: e.g. "active", "closed".

### Automatic Release Discovery
LeadEngine dynamically checks the public S3 XML index of the Overture bucket and queries the latest active release (e.g. `2026-10-21.0`), preventing failures when older snapshot partitions are deprecated.

---

## 2. OpenStreetMap (OSM) via Overpass API

### Overview
OpenStreetMap is a collaborative, volunteer-maintained open map of the world. LeadEngine queries the Overpass API to discover local businesses, cafes, hotels, and agencies.

### Tag Mapping by Vertical
- **Restaurants & Bars**:
  - `amenity=restaurant`
  - `amenity=cafe`
  - `amenity=bar`
  - `amenity=pub`
- **Hospitality**:
  - `tourism=hotel`
  - `tourism=guest_house`
  - `tourism=resort`
  - `tourism=hostel`
  - `tourism=motel`
- **Real Estate**:
  - `office=estate_agent`
  - `office=property_management`

### Extracted Attributes
- `name`: Business name.
- `website`, `contact:website`, `url`: Official site.
- `phone`, `contact:phone`: Phone numbers.
- `email`, `contact:email`: Public email addresses.
- `contact:instagram`, `contact:facebook`, `contact:linkedin`: Social URLs.
- `addr:street`, `addr:housenumber`, `addr:city`, `addr:postcode`: Physical address.
- `lat`, `lon` (or centroid for areas/ways): Coordinates.

### Resilience & Compliant Usage
- Identifies with custom `User-Agent` and contact email.
- Fallback mirror pool: Automatically falls back between `overpass-api.de`, `lz4.overpass-api.de`, `z.overpass-api.de`, and `overpass.kumi.systems` if any single server returns 502/timeout.
- Local disk caching: Overpass responses are cached locally for 7 days in `data/cache/osm/` to prevent redundant requests.

---

## 3. Market Geocoding (Nominatim)

### Overview
OpenStreetMap Nominatim is used only for converting human queries (e.g. "Austin, Texas, USA") into bounding boxes.

### Usage Safeguards
- **Curated Offline Dictionary**: Common markets (Austin, Miami, London, Manchester, Paris, etc.) are pre-configured offline and require 0 network calls.
- **Permanent Local Cache**: Any resolved market is cached permanently in `data/market_cache.json`.
- **Strict Rate Limiting**: Maximum 1 request per 1.1 seconds.
- **Never used for bulk scanning**: Only called once per new market query.

---

## 4. DNS MX Records (dnspython)
- Performs standard RFC DNS queries for Mail Exchange (`MX`) records for extracted email domains.
- Distinguishes `VALID_DOMAIN`, `NO_MX`, and `INVALID_SYNTAX`.
- Does not conduct aggressive SMTP probing or mailbox verification.
