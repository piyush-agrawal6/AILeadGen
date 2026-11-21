"""Organization context resolution and membership services.

Authentication identifies the USER; organization membership identifies which
company's data they may access. Every tenant-scoped request resolves its
organization here — never from browser-supplied identifiers.
"""
import json
import re
import uuid
from app.database.prospects import now

ROLE_ORDER = ('OWNER', 'ADMIN', 'MEMBER', 'VIEWER')
# Membership roles map onto the workspace RBAC verbs used by permissions.authorize.
ROLE_ALIASES = {'OWNER': 'OWNER', 'ADMIN': 'ADMIN', 'MEMBER': 'OPERATOR', 'VIEWER': 'VIEWER'}
PRODUCTS = ('LEADGEN', 'INTENT_RADAR', 'SEARCH_VISIBILITY')


class OrganizationError(RuntimeError):
    pass


def ensure_user(c, email, *, name=None, avatar_url=None):
    """Return the users row, creating it on first sight. Email is the stable key."""
    row = c.execute("SELECT id,display_name,avatar_url FROM users WHERE id=? AND email=?", (email,email)).fetchone()
    if row:
        return dict(row)
    stamp = now()
    # Concurrent first sign-ins can collide on either unique index in PostgreSQL.
    # Re-read the exact identity after both conflicts instead of adopting any row
    # merely because its email or ID conflicts.
    c.execute("INSERT INTO users(id,email,display_name,avatar_url,role,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT DO NOTHING",
              (email, email, name or email.split('@')[0], avatar_url, 'ADMIN', stamp))
    row=c.execute('SELECT id,display_name,avatar_url FROM users WHERE id=? AND email=?',(email,email)).fetchone()
    if not row:raise OrganizationError('Account identity requires administrator review.')
    return dict(row)


def memberships(c, email):
    rows = c.execute("""SELECT m.id,m.organization_id,m.role,m.status,m.created_at,
        o.name,o.slug,o.status AS organization_status
        FROM organization_memberships m JOIN organizations o ON o.id=m.organization_id
        WHERE m.user_id=? AND m.status='ACTIVE' AND o.status='ACTIVE'
        ORDER BY m.created_at,m.id""", (email,)).fetchall()
    return [dict(r) for r in rows]


def onboarding(c, organization_id):
    row = c.execute("SELECT * FROM organization_onboarding WHERE organization_id=?", (organization_id,)).fetchone()
    return dict(row) if row else None


def resolve(c, email):
    """Resolve the active organization for a user, or None when they have none.

    The gated personal preference is always rechecked against live membership.
    Legacy deployments retain their established earliest-membership behavior.
    """
    # Resolve memberships, saved selection and onboarding in one current SQL
    # snapshot. No permission result is cached across requests or provider work.
    from app.config.settings import get_settings
    records=[dict(r) for r in c.execute("""SELECT m.id,m.organization_id,m.role,m.status,m.created_at,
        o.name,o.slug,o.status AS organization_status,p.active_organization_id preferred_id,
        b.status onboarding_status,b.current_step onboarding_current_step,
        s.preferences_json setup_preferences_json
        FROM organization_memberships m JOIN organizations o ON o.id=m.organization_id
        LEFT JOIN user_profiles p ON p.user_id=m.user_id
        LEFT JOIN organization_onboarding b ON b.organization_id=m.organization_id
        LEFT JOIN organization_setup s ON s.organization_id=m.organization_id
        WHERE m.user_id=? AND m.status='ACTIVE' AND o.status='ACTIVE'
        ORDER BY m.created_at,m.id""",(email,)).fetchall()]
    if not records:return None
    active=records[0]
    if get_settings().heysow_workspace_management_enabled:
        preferred=records[0]['preferred_id']
        if preferred:
            active=next((r for r in records if r['organization_id']==preferred),None)
            if active is None:return None
        elif len(records)>1:return None
    deferred=False
    try:
        if active.get('setup_preferences_json'):
            deferred=bool(json.loads(active['setup_preferences_json']).get('setup_deferred',False))
    except (ValueError,TypeError,AttributeError):
        deferred=False
    private={'preferred_id','onboarding_status','onboarding_current_step','setup_preferences_json'}
    rows=[{key:value for key,value in r.items() if key not in private} for r in records]
    return {
        'organization_id':active['organization_id'],'organization_name':active['name'],
        'organization_slug':active['slug'],'role':active['role'],'memberships':rows,
        'onboarding_status':active['onboarding_status'] or 'NOT_STARTED',
        'onboarding_current_step':active['onboarding_current_step'],
        'onboarding_deferred':deferred,
    }


def products(c, organization_id):
    rows = c.execute("SELECT product,enabled FROM organization_products WHERE organization_id=?", (organization_id,)).fetchall()
    enabled = {r[0] for r in rows if r[1]}
    from app.config.settings import get_settings
    if get_settings().billing_enabled:
        from app.billing.service import granted
        enabled.update(granted(c,organization_id))
    if not get_settings().lead_engine_available:
        enabled.discard('LEADGEN')
    return {product: (product in enabled) for product in PRODUCTS}


def slugify(value):
    slug = ''.join(ch if ch.isalnum() else '-' for ch in (value or '').lower()).strip('-')
    while '--' in slug:
        slug = slug.replace('--', '-')
    return slug[:60] or 'company'


def unique_slug(c, name):
    base = slugify(name)
    slug = base
    suffix = 2
    while c.execute("SELECT 1 FROM organizations WHERE slug=?", (slug,)).fetchone():
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


def create_organization(c, email, name, *, setup_method='MANUAL',billing_account=None):
    """Create an organization, owner membership and onboarding state atomically.

    The organization may exist before onboarding finishes (recoverable onboarding),
    but access to product routes stays blocked until onboarding is COMPLETED.
    """
    if not (name and str(name).strip()):
        raise OrganizationError('Company name is required.')
    name = str(name).strip()
    ensure_user(c, email)
    stamp = now()
    organization_id = str(uuid.uuid4())
    slug = unique_slug(c, name)
    c.execute("INSERT INTO organizations(id,name,slug,status,created_by_user_id,created_at,updated_at) "
              "VALUES(?,?,?,?,?,?,?)", (organization_id, name, slug, 'ACTIVE', email, stamp, stamp))
    c.execute("INSERT INTO organization_memberships(id,organization_id,user_id,role,status,created_at,updated_at) "
              "VALUES(?,?,?,?, 'ACTIVE',?,?)", (str(uuid.uuid4()), organization_id, email, 'OWNER', stamp, stamp))
    c.execute("INSERT INTO organization_onboarding(organization_id,status,current_step,setup_method,created_at,updated_at) "
              "VALUES(?,'IN_PROGRESS','OBJECTIVES',?,?,?)", (organization_id, setup_method, stamp, stamp))
    try:
        c.execute("INSERT INTO organization_setup(organization_id,revision,current_step,objectives_json,preferences_json,updated_by,updated_at) "
                  "VALUES(?,0,'OBJECTIVES','[]','{}',?,?) ON CONFLICT(organization_id) DO NOTHING", (organization_id, email, stamp))
    except Exception:
        pass
    from app.config.settings import get_settings
    initial_products=[('INTENT_RADAR',0),('SEARCH_VISIBILITY',0)]
    if get_settings().database_schema_profile!='intent-radar-v1':
        initial_products.append(('LEADGEN',int(get_settings().lead_engine_public_enabled)))
    for product, enabled in initial_products:
        c.execute("INSERT INTO organization_products(organization_id,product,enabled,created_at,updated_at) "
                  "VALUES(?,?,?,?,?) ON CONFLICT(organization_id,product) DO NOTHING",
                  (organization_id, product, enabled, stamp, stamp))
    c.execute("INSERT INTO audit_log(id,actor,action,entity,result,details_json,organization_id,created_at) "
              "VALUES(?,?,?,?,?,?,?,?)",
              (str(uuid.uuid4()), email, 'ORGANIZATION_CREATED', f'organization:{organization_id}', 'SUCCESS',
               json.dumps({'name': name, 'slug': slug, 'setup_method': setup_method}), organization_id, stamp))
    settings_obj = get_settings()
    from app.billing.accounts import register
    register(c,organization_id,email,billing_account)
    if settings_obj.heysow_access_periods_enabled and c.execute("SELECT 1 FROM customer_accounts WHERE user_id=? AND status='ACTIVE' AND verified_at IS NOT NULL",(email,)).fetchone():
        # Every workspace created by a new commercial account stays managed;
        # creating a second workspace cannot recover unrestricted Beta access.
        c.execute('INSERT INTO customer_workspace_access(organization_id,registered_by,created_at) VALUES(?,?,?)',(organization_id,email,stamp))
        from app.billing.subscription_access import enroll
        enroll(c,email,organization_id)
    elif settings_obj.subscription_onboarding_required:
        # Ensure newly created secondary workspaces owned by allowlisted/existing
        # accounts also enter the legitimate subscription/activation lifecycle
        # instead of landing in an unresolvable restricted state.
        from app.billing.subscription_access import enroll
        enroll(c,email,organization_id)
    # Return the newly created workspace rather than an older active preference.
    # This helper does not silently change an existing session's selection.
    member=next(row for row in memberships(c,email) if row['organization_id']==organization_id)
    return {'organization_id':organization_id,'organization_name':member['name'],
            'organization_slug':member['slug'],'role':member['role'],
            'memberships':memberships(c,email),'onboarding_status':'IN_PROGRESS',
            'onboarding_current_step':'COMPANY'}


def complete_onboarding(c, organization_id):
    stamp = now()
    c.execute("""UPDATE organization_onboarding SET status='COMPLETED',profile_completed=1,services_completed=1,
        audience_completed=1,preferences_completed=1,completed_at=COALESCE(completed_at,?),updated_at=? 
        WHERE organization_id=?""", (stamp, stamp, organization_id))


def membership_role(c, email, organization_id):
    row = c.execute("SELECT m.role FROM organization_memberships m JOIN organizations o ON o.id=m.organization_id WHERE m.organization_id=? AND m.user_id=? AND m.status='ACTIVE' AND o.status='ACTIVE'",
                    (organization_id, email)).fetchone()
    return row[0] if row else None


def require_role(c, email, organization_id, allowed):
    role = membership_role(c, email, organization_id)
    if role not in allowed:
        from fastapi import HTTPException
        raise HTTPException(403, 'This action requires an elevated company role.')
    return role


def organization_id(request):
    """The tenant resolved server-side for this request (never browser-supplied)."""
    return getattr(request.state, 'organization_id', None)


def require_organization(request):
    """Raise unless the request carries a resolved organization context."""
    from fastapi import HTTPException
    org = organization_id(request)
    if not org:
        raise HTTPException(403, 'Create your company to continue.')
    return org


def workspace_settings(c, organization):
    """Organization-scoped LeadGen workspace settings (shared_settings)."""
    if not organization:
        return None
    # Current runtime requires the organization-settings migration. Reading the
    # immutable schema version on every lookup adds redundant page queries.
    row = c.execute("SELECT configuration_json FROM organization_settings WHERE organization_id=?",
                    (organization,)).fetchone()
    return json.loads(row[0]) if row else None


def save_workspace_settings(c, organization, data, actor):
    if not organization:
        raise OrganizationError('An organization context is required to change workspace settings.')
    stamp = now()
    from app.platform.context import organization as active_organization
    active_organization(organization)
    c.execute("""INSERT INTO organization_settings(organization_id,configuration_json,updated_by,updated_at)
        VALUES(?,?,?,?) ON CONFLICT(organization_id) DO UPDATE SET configuration_json=excluded.configuration_json,
        updated_by=excluded.updated_by,updated_at=excluded.updated_at""",
              (organization, json.dumps(data), actor, stamp))
