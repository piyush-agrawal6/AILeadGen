import json
import logging
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
from pydantic import BaseModel
import httpx

from app.config.settings import get_settings

logger = logging.getLogger("leadengine.markets")


class BoundingBox(BaseModel):
    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float

    def to_tuple(self) -> Tuple[float, float, float, float]:
        return (self.min_lat, self.min_lon, self.max_lat, self.max_lon)

    def contains(self, lat: float, lon: float) -> bool:
        return self.min_lat <= lat <= self.max_lat and self.min_lon <= lon <= self.max_lon


class MarketInfo(BaseModel):
    query: str
    city: str
    state: str
    country: str
    country_code: str
    bbox: BoundingBox
    center_lat: float
    center_lon: float
    cached: bool = False


# Curated offline markets for immediate instant resolution without external requests
CURATED_MARKETS: Dict[str, MarketInfo] = {
    "austin, texas, usa": MarketInfo(
        query="Austin, Texas, USA",
        city="Austin",
        state="Texas",
        country="United States",
        country_code="US",
        bbox=BoundingBox(min_lat=30.098, min_lon=-97.938, max_lat=30.516, max_lon=-97.561),
        center_lat=30.2672,
        center_lon=-97.7431,
        cached=True,
    ),
    "austin, tx": MarketInfo(
        query="Austin, TX",
        city="Austin",
        state="Texas",
        country="United States",
        country_code="US",
        bbox=BoundingBox(min_lat=30.098, min_lon=-97.938, max_lat=30.516, max_lon=-97.561),
        center_lat=30.2672,
        center_lon=-97.7431,
        cached=True,
    ),
    "austin": MarketInfo(
        query="Austin",
        city="Austin",
        state="Texas",
        country="United States",
        country_code="US",
        bbox=BoundingBox(min_lat=30.098, min_lon=-97.938, max_lat=30.516, max_lon=-97.561),
        center_lat=30.2672,
        center_lon=-97.7431,
        cached=True,
    ),
    "miami, florida, usa": MarketInfo(
        query="Miami, Florida, USA",
        city="Miami",
        state="Florida",
        country="United States",
        country_code="US",
        bbox=BoundingBox(min_lat=25.709, min_lon=-80.319, max_lat=25.855, max_lon=-80.139),
        center_lat=25.7617,
        center_lon=-80.1918,
        cached=True,
    ),
    "london, uk": MarketInfo(
        query="London, UK",
        city="London",
        state="England",
        country="United Kingdom",
        country_code="GB",
        bbox=BoundingBox(min_lat=51.286, min_lon=-0.510, max_lat=51.691, max_lon=0.334),
        center_lat=51.5074,
        center_lon=-0.1278,
        cached=True,
    ),
    "manchester, uk": MarketInfo(
        query="Manchester, UK",
        city="Manchester",
        state="England",
        country="United Kingdom",
        country_code="GB",
        bbox=BoundingBox(min_lat=53.339, min_lon=-2.355, max_lat=53.560, max_lon=-2.140),
        center_lat=53.4808,
        center_lon=-2.2426,
        cached=True,
    ),
    "paris, france": MarketInfo(
        query="Paris, France",
        city="Paris",
        state="Île-de-France",
        country="France",
        country_code="FR",
        bbox=BoundingBox(min_lat=48.815, min_lon=2.224, max_lat=48.902, max_lon=2.469),
        center_lat=48.8566,
        center_lon=2.3522,
        cached=True,
    ),
}

_CACHE_FILE = Path("data/market_cache.json")
_last_request_time = 0.0


def _load_disk_cache() -> Dict[str, dict]:
    if _CACHE_FILE.exists():
        try:
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_disk_cache(cache: Dict[str, dict]) -> None:
    _CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        logger.warning(f"Could not save market cache: {e}")


def resolve_market(
    market_str: str,
    custom_bbox: Optional[Tuple[float, float, float, float]] = None
) -> MarketInfo:
    """Resolve a human market string to city, state, country, and bounding box."""
    global _last_request_time
    clean_query = market_str.strip()
    norm_key = clean_query.lower()

    if custom_bbox:
        min_lat, min_lon, max_lat, max_lon = custom_bbox
        return MarketInfo(
            query=clean_query,
            city=clean_query.split(",")[0].strip(),
            state="",
            country="",
            country_code="",
            bbox=BoundingBox(min_lat=min_lat, min_lon=min_lon, max_lat=max_lat, max_lon=max_lon),
            center_lat=(min_lat + max_lat) / 2.0,
            center_lon=(min_lon + max_lon) / 2.0,
            cached=False,
        )

    # 1. Check curated offline dictionary
    if norm_key in CURATED_MARKETS:
        return CURATED_MARKETS[norm_key]

    # 2. Check local disk cache
    disk_cache = _load_disk_cache()
    if norm_key in disk_cache:
        data = disk_cache[norm_key]
        return MarketInfo(**data, cached=True)

    # 3. Resolve via Nominatim with rate limiting
    settings = get_settings()
    elapsed = time.time() - _last_request_time
    if elapsed < 1.1:
        time.sleep(1.1 - elapsed)

    headers = {
        "User-Agent": settings.crawler_user_agent,
    }
    if settings.crawler_contact_email:
        headers["From"] = settings.crawler_contact_email

    params = {
        "q": clean_query,
        "format": "jsonv2",
        "addressdetails": "1",
        "limit": "1",
    }

    logger.info(f"Geocoding market query '{clean_query}' via Nominatim...")
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.get(settings.nominatim_url, params=params, headers=headers)
            _last_request_time = time.time()
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.error(f"Failed to geocode market '{clean_query}': {e}")
        # Fallback heuristic if geocoder fails: check if any curated market matches partially
        for k, v in CURATED_MARKETS.items():
            if norm_key in k or k in norm_key:
                logger.info(f"Using partial curated fallback: {v.query}")
                return v
        raise ValueError(f"Could not resolve market '{clean_query}' and no cache available: {e}")

    if not data:
        raise ValueError(f"No geographic results found for market '{clean_query}'")

    item = data[0]
    bbox_raw = item.get("boundingbox", [])
    if len(bbox_raw) < 4:
        raise ValueError(f"Invalid bounding box returned for '{clean_query}'")

    # Nominatim returns [min_lat, max_lat, min_lon, max_lon] as strings
    min_lat = float(bbox_raw[0])
    max_lat = float(bbox_raw[1])
    min_lon = float(bbox_raw[2])
    max_lon = float(bbox_raw[3])

    address = item.get("address", {})
    city = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("municipality")
        or address.get("county")
        or clean_query.split(",")[0].strip()
    )
    state = address.get("state") or address.get("region") or ""
    country = address.get("country") or ""
    country_code = (address.get("country_code") or "").upper()

    lat = float(item.get("lat", (min_lat + max_lat) / 2.0))
    lon = float(item.get("lon", (min_lon + max_lon) / 2.0))

    info = MarketInfo(
        query=clean_query,
        city=city,
        state=state,
        country=country,
        country_code=country_code,
        bbox=BoundingBox(min_lat=min_lat, min_lon=min_lon, max_lat=max_lat, max_lon=max_lon),
        center_lat=lat,
        center_lon=lon,
        cached=False,
    )

    # Save to disk cache permanently
    disk_cache[norm_key] = info.model_dump()
    _save_disk_cache(disk_cache)

    return info
