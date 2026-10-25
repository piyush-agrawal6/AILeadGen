import json
import logging
from typing import List, Optional
import duckdb
import httpx
from bs4 import BeautifulSoup

from app.config.markets import MarketInfo
from app.config.settings import get_settings
from app.config.verticals import VerticalDefinition
from app.database.models import Business, ProcessingStatus
from app.discovery.base import BaseDiscoveryProvider
from app.normalization.businesses import normalize_business

logger = logging.getLogger("leadengine.discovery.overture")

_CACHED_RELEASE: Optional[str] = None


def get_latest_overture_release(s3_region: str = "us-west-2") -> str:
    """Discover the latest available Overture Maps release from public S3 index."""
    global _CACHED_RELEASE
    if _CACHED_RELEASE:
        return _CACHED_RELEASE

    default_release = "2026-10-21.0"
    url = f"https://overturemaps-{s3_region}.s3.amazonaws.com/?prefix=release/&delimiter=/"
    try:
        with httpx.Client(timeout=6.0) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, "xml")
                prefixes = [
                    p.get_text().strip("release/").strip("/")
                    for p in soup.find_all("Prefix")
                    if p.get_text() != "release/"
                ]
                if prefixes:
                    sorted_prefixes = sorted(prefixes, reverse=True)
                    _CACHED_RELEASE = sorted_prefixes[0]
                    logger.info(f"Auto-discovered latest Overture Maps release: {_CACHED_RELEASE}")
                    return _CACHED_RELEASE
    except Exception as e:
        logger.debug(f"Could not auto-discover Overture release: {e}")

    _CACHED_RELEASE = default_release
    return _CACHED_RELEASE


class OvertureDiscoveryProvider(BaseDiscoveryProvider):
    @property
    def name(self) -> str:
        return "Overture Maps"

    def search(
        self,
        market: MarketInfo,
        vertical: VerticalDefinition,
        limit: int = 500,
    ) -> List[Business]:
        settings = get_settings()
        s3_region = settings.overture_s3_region or settings.discovery.overture_s3_region or "us-west-2"
        release = settings.overture_release or settings.discovery.overture_release
        if not release or release.startswith("2024-"):
            release = get_latest_overture_release(s3_region)

        parquet_path = f"s3://overturemaps-{s3_region}/release/{release}/theme=places/type=place/*"
        logger.info(f"Querying Overture Places ({release}) for {market.city} [{vertical.display_name}]...")

        # Build category filter list
        categories = vertical.overture_categories or [vertical.key]
        cat_conditions = " OR ".join(
            f"lower(COALESCE(basic_category, '')) LIKE '%{cat.lower()}%' OR lower(COALESCE(taxonomy['primary'], '')) LIKE '%{cat.lower()}%'"
            for cat in categories
        )

        bbox = market.bbox
        query = f"""
            SELECT
                id,
                names['primary'] AS name,
                COALESCE(basic_category, taxonomy['primary']) AS category,
                CASE WHEN websites IS NOT NULL AND len(websites) > 0 THEN websites[1] ELSE NULL END AS website,
                CASE WHEN emails IS NOT NULL AND len(emails) > 0 THEN emails[1] ELSE NULL END AS email,
                CASE WHEN phones IS NOT NULL AND len(phones) > 0 THEN phones[1] ELSE NULL END AS phone,
                CASE WHEN socials IS NOT NULL AND len(socials) > 0 THEN socials[1] ELSE NULL END AS social,
                CASE WHEN addresses IS NOT NULL AND len(addresses) > 0 THEN addresses[1]['freeform'] ELSE NULL END AS address,
                CASE WHEN addresses IS NOT NULL AND len(addresses) > 0 THEN addresses[1]['postcode'] ELSE NULL END AS postcode,
                bbox['xmin'] AS min_lon,
                bbox['ymin'] AS min_lat,
                confidence,
                operating_status
            FROM read_parquet('{parquet_path}')
            WHERE bbox['xmin'] >= {bbox.min_lon}
              AND bbox['xmax'] <= {bbox.max_lon}
              AND bbox['ymin'] >= {bbox.min_lat}
              AND bbox['ymax'] <= {bbox.max_lat}
              AND ({cat_conditions})
            LIMIT {limit}
        """

        businesses: List[Business] = []
        con = None
        try:
            con = duckdb.connect()
            con.execute("INSTALL httpfs; LOAD httpfs;")
            con.execute(f"SET s3_region='{s3_region}';")

            df = con.execute(query).fetchdf()
            for _, row in df.iterrows():
                name = str(row.get("name") or "").strip()
                if not name:
                    continue

                b = Business(
                    external_overture_id=str(row.get("id")),
                    name=name,
                    normalized_name="",
                    vertical=vertical.key,
                    subcategory=str(row.get("category") or ""),
                    country=market.country,
                    country_code=market.country_code,
                    state=market.state,
                    city=market.city,
                    postcode=str(row.get("postcode") or "") if row.get("postcode") else None,
                    address=str(row.get("address") or "") if row.get("address") else None,
                    latitude=float(row.get("min_lat")) if row.get("min_lat") is not None else None,
                    longitude=float(row.get("min_lon")) if row.get("min_lon") is not None else None,
                    phone=str(row.get("phone") or "") if row.get("phone") else None,
                    website=str(row.get("website") or "") if row.get("website") else None,
                    public_email=str(row.get("email") or "") if row.get("email") else None,
                    source_overture=True,
                    source_osm=False,
                    source_confidence=float(row.get("confidence") or 0.7),
                    operating_status=str(row.get("operating_status") or "active"),
                    processing_status=ProcessingStatus.DISCOVERED.value,
                )
                b = normalize_business(b)
                businesses.append(b)

            logger.info(f"Overture Maps returned {len(businesses)} raw records.")
        except Exception as e:
            logger.warning(
                f"Overture Maps discovery query failed: {e}. "
                "Falling back to OpenStreetMap / secondary discovery."
            )
        finally:
            if con:
                try:
                    con.close()
                except Exception:
                    pass

        return businesses
