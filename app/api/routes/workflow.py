from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from app.api.dependencies import get_db
from app.config.settings import get_settings
from app.database.repositories import BusinessRepository
from app.database.prospects import ProspectRepository

router = APIRouter(tags=["Collaboration"])
Status = Literal['NEW','SHORTLISTED','READY_TO_CONTACT','CONTACTED','FOLLOW_UP','REPLIED','MEETING','PROPOSAL','WON','LOST','NOT_INTERESTED','DO_NOT_CONTACT']


class WorkflowChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lead_status: Status | None = None
    assigned_to: str | None = Field(default=None, max_length=254)


class NoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    body: str = Field(min_length=1, max_length=5000)


def require_prospect(conn, lead_id, actor):
    if getattr(conn,'backend',None)=='postgres':conn.execute('SELECT pg_advisory_xact_lock(691944307)')
    from app.database.phase36_schema import phase36_ready
    if phase36_ready(conn) and conn.execute('SELECT 1 FROM deletion_targets WHERE business_id=?',(lead_id,)).fetchone():
        raise HTTPException(409,'This lead is being permanently deleted. Finish or retry its deletion first.')
    business = BusinessRepository(conn).get_by_id(lead_id)
    if not business:
        raise HTTPException(404, "Lead not found.")
    repo = ProspectRepository(conn)
    row = conn.execute("SELECT prospect_id FROM businesses WHERE id=?", (lead_id,)).fetchone()
    return row[0] or repo.observe(business, created_by=actor)


@router.get("/users")
def users(request: Request, conn=Depends(get_db)):
    repo = ProspectRepository(conn)
    for email in get_settings().allowed_emails:
        repo.user(email)
    return [dict(r) for r in conn.execute("SELECT id,email,display_name,avatar_url,role FROM users ORDER BY email").fetchall()]


@router.get("/leads/{lead_id}/workspace")
def workspace(lead_id: int, request: Request, conn=Depends(get_db)):
    require_prospect(conn, lead_id, request.state.user_email)
    return ProspectRepository(conn).dossier(lead_id)


@router.patch("/leads/{lead_id}/workflow")
def update_workflow(lead_id: int, update: WorkflowChange, request: Request, conn=Depends(get_db)):
    if update.assigned_to and update.assigned_to not in get_settings().allowed_emails:
        raise HTTPException(422, "Assignment must use an approved team member.")
    prospect_id = require_prospect(conn, lead_id, request.state.user_email)
    changes = {key: getattr(update, key) for key in update.model_fields_set}
    ProspectRepository(conn).workflow(prospect_id, request.state.user_email, **changes)
    return ProspectRepository(conn).dossier(lead_id)


@router.post("/leads/{lead_id}/notes", status_code=201)
def add_note(lead_id: int, note: NoteCreate, request: Request, conn=Depends(get_db)):
    body = note.body.strip()
    if not body:
        raise HTTPException(422, "Write a note before saving.")
    repo = ProspectRepository(conn)
    prospect_id = require_prospect(conn, lead_id, request.state.user_email)
    repo.add_note(prospect_id, request.state.user_email, body)
    return repo.dossier(lead_id)
