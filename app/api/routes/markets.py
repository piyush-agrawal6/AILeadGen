from typing import Any, Dict, List
from fastapi import APIRouter
from pydantic import BaseModel

from app.config.markets import CURATED_MARKETS

router = APIRouter(prefix="/markets", tags=["Markets"])


@router.get("/presets")
def presets():
    from app.config.presets import market_presets
    return market_presets()


class MarketItem(BaseModel):
    query: str
    city: str
    state: str
    country: str
    country_code: str
    center_lat: float
    center_lon: float


@router.get("", response_model=List[MarketItem])
def list_markets():
    """List curated and recommended discovery markets."""
    results = []
    seen = set()
    for m in CURATED_MARKETS.values():
        key = (m.city, m.state, m.country)
        if key not in seen:
            seen.add(key)
            results.append(
                MarketItem(
                    query=m.query,
                    city=m.city,
                    state=m.state,
                    country=m.country,
                    country_code=m.country_code,
                    center_lat=m.center_lat,
                    center_lon=m.center_lon,
                )
            )
    return results
