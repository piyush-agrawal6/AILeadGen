"""Universal Workspace Search API — strictly workspace-scoped and RBAC-enforced."""
from fastapi import APIRouter, Depends, Query, Request
from app.api.dependencies import get_db
from app.platform.workspace_search import search_workspace

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("")
def global_search(
    request: Request,
    q: str = Query("", max_length=160),
    category: str = Query("all", max_length=32),
    limit: int = Query(6, ge=1, le=15),
    c=Depends(get_db, scope="function"),
):
    actor = getattr(request.state, "user_email", "")
    org = getattr(request.state, "organization_id", None)
    return search_workspace(
        c,
        organization_id=org,
        actor=actor,
        query=q,
        category=category,
        limit=limit,
    )
