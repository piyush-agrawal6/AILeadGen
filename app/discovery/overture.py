import json
import os
import threading
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
from app.discovery.source_metadata import source_metadata,optional_text

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
        import re
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}\.\d+",release) or not re.fullmatch(r"[a-z]+-[a-z]+-\d",s3_region):
            raise ValueError("Invalid configured Overture release or region")

        parquet_path = f"s3://overturemaps-{s3_region}/release/{release}/theme=places/type=place/*"
        logger.info(f"Querying Overture Places ({release}) for {market.city} [{vertical.display_name}]...")

        # Build category filter list with strict word/token boundaries
        categories = vertical.overture_categories or [vertical.key]
        cond_list = []
        for cat in categories:
            c = cat.lower().strip()
            import re
            if not re.fullmatch(r"[a-z0-9_]+", c):
                raise ValueError("Invalid configured taxonomy category")
            cond_list.append(
                f"(lower(COALESCE(taxonomy['primary'], '')) = '{c}' "
                f"OR list_contains(taxonomy['hierarchy'], '{c}') "
                f"OR lower(COALESCE(basic_category, '')) = '{c}')"
            )
        if vertical.key == "restaurant":
            cond_list.append("lower(COALESCE(basic_category, '')) = 'eat_and_drink'")
        elif vertical.key == "hospitality":
            cond_list.append("lower(COALESCE(basic_category, '')) = 'accommodation'")
        elif vertical.key == "real_estate":
            cond_list.append("lower(COALESCE(basic_category, '')) = 'real_estate'")

        cat_conditions = " OR ".join(cond_list)

        bbox = market.bbox
        query = f"""
            SELECT
                id,
                names['primary'] AS name,
                basic_category AS basic_category,
                taxonomy['primary'] AS primary_taxonomy,
                to_json(taxonomy) AS taxonomy_json,
                COALESCE(basic_category, taxonomy['primary']) AS category,
                CASE WHEN websites IS NOT NULL AND len(websites) > 0 THEN websites[1] ELSE NULL END AS website,
                CASE WHEN emails IS NOT NULL AND len(emails) > 0 THEN emails[1] ELSE NULL END AS email,
                CASE WHEN phones IS NOT NULL AND len(phones) > 0 THEN phones[1] ELSE NULL END AS phone,
                CASE WHEN socials IS NOT NULL AND len(socials) > 0 THEN socials[1] ELSE NULL END AS social,
                to_json(socials) AS socials_json,
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
            con.execute("SET memory_limit='512MB'; SET threads=1; SET max_temp_directory_size='128MB';")
            if directory := os.environ.get("DUCKDB_EXTENSION_DIRECTORY"):
                con.execute("SET extension_directory=?",[directory])
            con.execute("INSTALL httpfs; LOAD httpfs;")
            con.execute(f"SET s3_region='{s3_region}';")

            timer=threading.Timer(120,con.interrupt)
            timer.daemon=True;timer.start()
            try:
                df = con.execute(query).fetchdf()
            finally:
                timer.cancel()
            for _, row in df.iterrows():
                name = optional_text(row.get('name')) or ''
                if not name:
                    continue

                primary_tax = optional_text(row.get('primary_taxonomy')) or ''
                basic_cat = optional_text(row.get('basic_category')) or ''
                subcat = primary_tax or optional_text(row.get('category')) or ''

                b = Business(
                    external_overture_id=str(row.get("id")),
                    name=name,
                    normalized_name="",
                    vertical=vertical.key,
                    subcategory=subcat if subcat else None,
                    source_category=basic_cat or subcat,
                    source_tags=source_metadata(row.get('taxonomy_json'),row.get('socials_json')),
                    country=market.country,
                    country_code=market.country_code,
                    state=market.state,
                    city=market.city,
                    postcode=optional_text(row.get('postcode')),
                    address=optional_text(row.get('address')),
                    latitude=float(row.get("min_lat")) if row.get("min_lat") is not None else None,
                    longitude=float(row.get("min_lon")) if row.get("min_lon") is not None else None,
                    phone=optional_text(row.get('phone')),
                    website=optional_text(row.get('website')),
                    public_email=optional_text(row.get('email')),
                    source_overture=True,
                    source_osm=False,
                    source_confidence=float(row.get("confidence") or 0.7),
                    operating_status=optional_text(row.get('operating_status')) or 'active',
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
