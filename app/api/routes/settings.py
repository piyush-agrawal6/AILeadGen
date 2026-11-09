from fastapi import APIRouter, Depends, Request
from app.api.dependencies import get_db
from app.api.organization import require_organization, workspace_settings, save_workspace_settings
from app.database.prospects import now
import json
from app.api.schemas.settings import (
    AppSettingsSchema,
    AuditingSettings,
    CrawlerSettings,
    DiscoverySettings,
    GeneralSettings,
    ScoringSettings,
)
from app.config.settings import get_settings

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("", response_model=AppSettingsSchema)
def get_app_settings(request: Request, conn=Depends(get_db,scope='function')):
    """Retrieve the organization's active system and pipeline configuration."""
    from app.config.workspace import load_settings
    return load_settings(conn,require_organization(request))

@router.put("", response_model=AppSettingsSchema)
def update_app_settings(updated: AppSettingsSchema, request: Request, conn=Depends(get_db,scope='function')):
    """Safely apply updated settings to this organization's pipeline configuration.

    Settings are stored per organization; process-global defaults are never
    mutated so one company's configuration cannot leak into another's runs.
    """
    organization = require_organization(request)
    if getattr(conn,'backend',None)=='postgres':conn.execute('SELECT pg_advisory_xact_lock(691944520)')
    current=workspace_settings(conn,organization) or {}
    stored={**current,**updated.model_dump()}
    if 'automation' in current:stored['automation']=current['automation']
    save_workspace_settings(conn,organization,stored,request.state.user_email)
    return updated
