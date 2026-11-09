"""Real isolated SQLite transactions; PostgreSQL still requires staging tests."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
import uuid
from fastapi import HTTPException
from app.database.connection import db_session
from app.database.migrations import run_migrations
from app.api.organization import create_organization
from app.platform.context import workspace_scope
from app.platform.invitations import create,respond,InviteCreate,InviteRespond
from app.platform.workspaces import create_workspace,WorkspaceCreate


def test_invitation_concurrent_acceptance_grants_exactly_one_membership(tmp_path):
    path=tmp_path/'concurrent-invite.db'
    with db_session(path) as c:
        run_migrations(c)
        org=create_organization(c,'owner@example.test','Concurrent company')['organization_id']
        with workspace_scope(c,'owner@example.test',org):invitation=create(c,InviteCreate(email='recipient@example.test'))
    barrier=Barrier(2)
    def accept():
        barrier.wait(timeout=10)
        try:
            with db_session(path) as c:return respond(c,'recipient@example.test',InviteRespond(token=invitation['token'],action='ACCEPT'))['status']
        except HTTPException as error:return error.status_code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:accept(),range(2)))
    assert sorted(str(item) for item in results)==['409','ACCEPTED']
    with db_session(path) as c:
        assert c.execute('SELECT COUNT(*) FROM organization_memberships WHERE organization_id=? AND user_id=?',(org,'recipient@example.test')).fetchone()[0]==1
        assert c.execute("SELECT COUNT(*) FROM workspace_notifications WHERE kind='INVITATION_ACCEPTED'").fetchone()[0]==1


def test_concurrent_workspace_creation_reuses_the_same_request(tmp_path):
    path=tmp_path/'concurrent-create.db'
    with db_session(path) as c:run_migrations(c)
    body=WorkspaceCreate(name='Concurrent creation',request_id=uuid.uuid4())
    barrier=Barrier(2)
    def make():
        barrier.wait(timeout=10)
        with db_session(path) as c:return create_workspace(c,'new-creator@example.test',body)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:make(),range(2)))
    assert len({item['organization_id'] for item in results})==1
    assert sorted(item['reused'] for item in results)==[False,True]
    with db_session(path) as c:
        assert c.execute('SELECT COUNT(*) FROM organization_memberships WHERE user_id=?',('new-creator@example.test',)).fetchone()[0]==1
        assert c.execute('PRAGMA foreign_key_check').fetchall()==[]
