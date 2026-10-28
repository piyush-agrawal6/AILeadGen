from typing import List
from fastapi import APIRouter
from pydantic import BaseModel

from app.config.verticals import VerticalManager

router = APIRouter(prefix="/verticals", tags=["Verticals"])


class VerticalItem(BaseModel):
    key: str
    display_name: str
    aliases: List[str]


@router.get("", response_model=List[VerticalItem])
def list_verticals():
    """List configured and supported industry verticals."""
    mgr = VerticalManager()
    results = []
    for key, v in mgr.verticals.items():
        results.append(
            VerticalItem(
                key=key,
                display_name=v.display_name,
                aliases=v.aliases,
            )
        )
    return results
