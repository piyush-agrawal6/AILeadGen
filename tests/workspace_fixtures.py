"""Explicit membership-backed scopes for historical internal-workspace fixtures."""
from app.database.organization_schema import PLANEBYTE_ORGANIZATION_ID
from app.platform.context import workspace_scope


def bind_internal_workspace(conn, request):
    row = conn.execute("SELECT created_by_user_id FROM organizations WHERE id=?", (PLANEBYTE_ORGANIZATION_ID,)).fetchone()
    if not row:
        raise AssertionError("Fixture must migrate and seed its isolated database first")
    scope = workspace_scope(conn, row[0], PLANEBYTE_ORGANIZATION_ID)
    scope.__enter__()
    request.addfinalizer(lambda: scope.__exit__(None, None, None))


def historical_observation(conn, business):
    """Seed pre-organization snapshots with historical SQL, not current services."""
    import uuid
    from app.database.prospects import now,identity_keys
    version=conn.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0] or 0
    assert version<16, 'Use the owned repository for current-schema fixtures'
    pid=str(uuid.uuid4());stamp=now()
    conn.execute('INSERT INTO prospects(id,first_seen_at,last_seen_at,updated_at) VALUES(?,?,?,?)',(pid,stamp,stamp,stamp))
    for key,kind in identity_keys(business):conn.execute('INSERT INTO business_identities(identity_key,prospect_id,evidence_type) VALUES(?,?,?)',(key,pid,kind))
    conn.execute('UPDATE businesses SET prospect_id=? WHERE id=?',(pid,business.id))
    conn.execute('INSERT INTO prospect_observations(prospect_id,run_id,business_id,observed_at) VALUES(?,?,?,?)',(pid,business.run_id,business.id,stamp))
    return pid


def workspace_template(conn):
    """Explicit customer template for general prospecting tests; never a fallback."""
    import uuid
    from app.platform.context import organization
    from app.api.routes.mail import save_template,Template
    key=str(uuid.uuid5(uuid.NAMESPACE_URL,'controlled-workspace-template:'+organization()))
    save_template(conn,key,Template(name='Controlled company introduction',category='General',subject='A conversation with {{business_name}}',body_text='Hi {{business_name}} team,\n\nWe help businesses organize their customer workflows and build reliable software. If this is relevant to your plans, reply and we can outline a practical approach.\n\n{{sender_company}}'),organization())
    return key
