import hashlib
import json
import logging
import time
from pathlib import Path
from typing import List, Optional
import httpx

from app.config.markets import MarketInfo
from app.config.settings import get_settings
from app.config.verticals import VerticalDefinition
from app.database.models import Business, ProcessingStatus
from app.discovery.base import BaseDiscoveryProvider
from app.normalization.businesses import normalize_business

logger = logging.getLogger("leadengine.discovery.osm")
CACHE_DIR = Path("data/cache/osm")

OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter",
    "https://z.overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]


class OSMDiscoveryProvider(BaseDiscoveryProvider):
    @property
    def name(self) -> str:
        return "OpenStreetMap"

    def search(
        self,
        market: MarketInfo,
        vertical: VerticalDefinition,
        limit: int = 1000,
    ) -> List[Business]:
        settings = get_settings()
        bbox = market.bbox
        s, w, n, e = bbox.min_lat, bbox.min_lon, bbox.max_lat, bbox.max_lon

        # Build QL tag filters
        tag_queries = []
        for tag in vertical.osm_tags:
            val_pattern = "|".join(tag.values)
            tag_queries.append(f'nwr["{tag.key}"~"^({val_pattern})$"]({s},{w},{n},{e});')

        if not tag_queries:
            tag_queries.append(f'nwr["amenity"="restaurant"]({s},{w},{n},{e});')

        query_body = "\n  ".join(tag_queries)
        overpass_ql = f"""
[out:json][timeout:60];
(
  {query_body}
);
out center {limit};
"""

        logger.info(f"Querying OpenStreetMap for {market.city} [{vertical.display_name}]...")
        data = self._fetch_overpass(overpass_ql, settings.overpass_url)
        if not data:
            return []

        elements = data.get("elements", [])
        logger.info(f"Overpass returned {len(elements)} elements.")

        businesses: List[Business] = []
        for elem in elements:
            tags = elem.get("tags", {})
            name = tags.get("name") or tags.get("brand") or tags.get("operator")
            if not name:
                continue

            elem_id = f"{elem.get('type')}/{elem.get('id')}"

            # Coordinates
            lat = elem.get("lat") or (elem.get("center", {}).get("lat") if "center" in elem else None)
            lon = elem.get("lon") or (elem.get("center", {}).get("lon") if "center" in elem else None)

            # Website
            website = tags.get("website") or tags.get("contact:website") or tags.get("url")

            # Phone
            phone = tags.get("phone") or tags.get("contact:phone")

            # Email
            email = tags.get("email") or tags.get("contact:email")

            # Socials
            instagram = tags.get("contact:instagram") or tags.get("instagram")
            facebook = tags.get("contact:facebook") or tags.get("facebook")
            linkedin = tags.get("contact:linkedin") or tags.get("linkedin")

            # Address
            street = tags.get("addr:street")
            housenumber = tags.get("addr:housenumber")
            full_address = None
            if street:
                full_address = f"{housenumber} {street}".strip() if housenumber else street
            postcode = tags.get("addr:postcode")
            city = tags.get("addr:city") or market.city

            # Subcategory
            subcategory = None
            for tag in vertical.osm_tags:
                if tag.key in tags:
                    subcategory = tags[tag.key]
                    break

            b = Business(
                external_osm_id=elem_id,
                name=name,
                normalized_name="",
                vertical=vertical.key,
                subcategory=subcategory,
                source_category=subcategory,
                source_tags=json.dumps(tags),
                country=market.country,
                country_code=market.country_code,
                state=market.state,
                city=city,
                postcode=postcode,
                address=full_address,
                latitude=float(lat) if lat is not None else None,
                longitude=float(lon) if lon is not None else None,
                phone=phone,
                website=website,
                public_email=email,
                instagram=instagram,
                facebook=facebook,
                linkedin=linkedin,
                source_overture=False,
                source_osm=True,
                source_confidence=0.8,
                operating_status="active",
                processing_status=ProcessingStatus.DISCOVERED.value,
            )
            b = normalize_business(b)
            businesses.append(b)

        return businesses

    def _fetch_overpass(self, query: str, primary_url: str) -> Optional[dict]:
        settings = get_settings()
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        query_hash = hashlib.sha256(query.encode("utf-8")).hexdigest()
        cache_path = CACHE_DIR / f"{query_hash}.json"

        # Check local cache (valid for 7 days)
        if cache_path.exists():
            try:
                mtime = cache_path.stat().st_mtime
                if time.time() - mtime < 7 * 86400:
                    with open(cache_path, "r", encoding="utf-8") as f:
                        logger.info("Loaded Overpass response from disk cache.")
                        return json.load(f)
            except Exception as e:
                logger.warning(f"Failed reading cache {cache_path}: {e}")

        headers = {
            "User-Agent": settings.crawler_user_agent,
        }
        if settings.crawler_contact_email:
            headers["From"] = settings.crawler_contact_email

        candidate_urls = [primary_url] + [u for u in OVERPASS_MIRRORS if u != primary_url]

        for url in candidate_urls:
            try:
                with httpx.Client(timeout=httpx.Timeout(45.0, connect=10.0)) as client:
                    resp = client.post(url, data={"data": query}, headers=headers)
                    if resp.status_code == 200:
                        data = resp.json()
                        try:
                            with open(cache_path, "w", encoding="utf-8") as f:
                                json.dump(data, f)
                        except Exception:
                            pass
                        return data
                    elif resp.status_code in (429, 502, 503, 504):
                        logger.warning(f"Overpass mirror {url} returned HTTP {resp.status_code}, trying next mirror...")
                        continue
            except Exception as e:
                logger.debug(f"Overpass error on {url}: {e}, trying next mirror...")
                continue

        logger.error("All Overpass mirrors timed out or returned errors.")
        return None
