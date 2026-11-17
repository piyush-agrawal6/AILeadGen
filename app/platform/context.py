"""Explicit, request-local trusted workspace context; no default organization."""
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from fastapi import HTTPException


@dataclass(frozen=True)
class WorkspaceContext:
    organization_id: str
    actor: str
    authority: str = "MEMBER"


_active: ContextVar[WorkspaceContext | None] = ContextVar("heysow_workspace", default=None)


def current():
    context = _active.get()
    if context is None:
        raise HTTPException(403, "A verified workspace context is required.")
    return context


def organization(expected=None):
    context = current()
    if expected is not None and expected != context.organization_id:
        raise HTTPException(404, "Resource not found in this workspace.")
    return context.organization_id


@contextmanager
def workspace_scope(conn, actor, organization_id):
    """Bind only an active member of an active organization, on every entry."""
    from app.api.organization import membership_role
    from app.config.settings import get_settings
    settings=get_settings()
    if settings.heysow_accounts_enabled:
        from app.accounts.policy import require_work_identity
        require_work_identity(actor)
    if actor not in settings.allowed_emails:
        if settings.heysow_customer_access_enabled:
            from app.platform.admission import access
            if not access(conn,actor):raise HTTPException(403,'Active account admission is required.')
        elif settings.app_env=='production':
            raise HTTPException(403,'Customer account access is not enabled.')
    if not actor or not organization_id or not membership_role(conn, actor, organization_id):
        raise HTTPException(403, "Active workspace membership is required.")
    # membership_role joins the active organization in the same query; a
    # second status read adds latency without an atomic authorization guarantee.
    previous = _active.get()
    if previous and previous.organization_id != organization_id:
        raise HTTPException(403, "A task cannot switch its workspace context.")
    token = _active.set(WorkspaceContext(organization_id, actor))
    try:
        yield current()
    finally:
        _active.reset(token)


def require_internal_mailbox():
    from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID
    context = current()
    if context.authority != 'MEMBER' or context.organization_id != PLANEBYTE_ORGANIZATION_ID:
        raise HTTPException(409, "Email connection is not configured for this workspace.")
    return context


@contextmanager
def tracking_scope(conn, token, action):
    """A validated opaque capability grants only its existing tracking action.

    It cannot connect to or send through a mailbox. The tenant comes from the
    stored token/message, never from URL parameters or posted organization IDs.
    """
    from app.mail.tracking import lookup
    row = lookup(conn, token, action)
    if not row or not row.get('organization_id'):
        raise HTTPException(404, 'Tracking link is unavailable.')
    previous = _active.get()
    if previous and previous.organization_id != row['organization_id']:
        raise HTTPException(404, 'Tracking link is unavailable.')
    marker = _active.set(WorkspaceContext(row['organization_id'], 'tracking-capability', 'TRACKING'))
    try:
        yield row
    finally:
        _active.reset(marker)


@contextmanager
def job_scope(conn, kind, identifier):
    """Worker-only entry: validate persisted owner and active membership.

    HTTP services must use the already-bound request scope. A job ID alone never
    grants access, and an existing scope cannot be switched to a different tenant.
    """
    import json
    if kind in ('acquisition','workflow','scan','report'):
        from app.config.settings import get_settings
        if not get_settings().lead_engine_available:
            raise HTTPException(404,'Lead Engine is unavailable for this workspace job.')
    tables = {"acquisition": ("acquisition_jobs", "owner"),
              "workflow": ("workflow_runs", "created_by"),
              "scan": ("pipeline_runs", None),
              "report": ("client_reports", "created_by"),
              "company_profile": ("organization_profile_jobs", "created_by"),
              "intelligence": ("intelligence_jobs", "created_by"),
              "webhook": ("webhook_endpoints", "created_by"),
              "sheet_export": ("organization_sheet_exports", "created_by")}
    if kind not in tables:
        raise ValueError("Unknown workspace job type")
    table, owner_field = tables[kind]
    row = conn.execute(f"SELECT * FROM {table} WHERE id=?", (identifier,)).fetchone()
    if not row or not row["organization_id"]:
        raise HTTPException(409, "Job has no verified workspace owner.")
    owner = row[owner_field] if owner_field else json.loads(row["run_configuration_json"] or "{}").get("created_by")
    with workspace_scope(conn, owner, row["organization_id"]) as context:
        if kind=='intelligence':
            from app.billing.subscription_access import require_product
            require_product(conn,context.organization_id)
        if kind in ('acquisition','workflow','scan','report'):
            from app.api.organization import products
            if not products(conn,context.organization_id).get('LEADGEN'):
                raise HTTPException(404,'Lead Engine is unavailable for this workspace job.')
        yield context
