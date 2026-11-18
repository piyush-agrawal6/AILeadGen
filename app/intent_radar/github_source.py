"""GitHub public/connected discovery, customer OAuth installation binding, and HMAC webhooks."""
import base64, hashlib, hmac, json, logging, re, secrets, uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from fastapi import HTTPException
from app.config.settings import get_settings
from app.database.connection import db_session
from app.database.prospects import now
from app.integrations.crypto import seal, open_envelope
from app.intent_radar import connectors, providers
from app.intent_radar.github_auth import GitHubAuth
from app.intent_radar.permissions import context
from app.intent_radar.source_http import JsonClient, ProviderFailure
from app.intent_radar.source_runtime import Gateway

logger = logging.getLogger(__name__)
REPO_RE = re.compile(r'^[A-Za-z0-9_.-]{1,100}/[A-Za-z0-9_.-]{1,100}$')


def _pkce_challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode('ascii')).digest()).rstrip(b'=').decode('ascii')


def _sanitize_repos(repos: list[str]) -> list[str]:
    clean = []
    for r in repos or []:
        val = str(r or '').strip().strip('/')
        if val.startswith('https://github.com/'):
            val = val.removeprefix('https://github.com/').strip('/')
        if not REPO_RE.fullmatch(val):
            raise HTTPException(422, f'Invalid GitHub repository format: {r!r}. Expected owner/repo.')
        if val not in clean:
            clean.append(val)
    return clean[:5]


def _configured_app() -> bool:
    s = get_settings()
    return bool(s.github_app_id and s.github_app_private_key.get_secret_value())


def _oauth_configured() -> bool:
    s = get_settings()
    return bool(s.github_app_client_id and s.github_app_client_secret.get_secret_value())


def connection_status(c) -> dict:
    org = context(c).organization_id
    row = c.execute('SELECT * FROM intent_github_connections WHERE organization_id=?', (org,)).fetchone()
    s = get_settings()
    base = {
        'app_configured': _configured_app(),
        'oauth_configured': _oauth_configured(),
        'webhooks_configured': bool(s.github_app_webhook_secret.get_secret_value() and s.intent_radar_github_webhooks_enabled),
        'public_search_available': bool(s.intent_radar_github_enabled and s.intent_radar_github_public_search_enabled and _configured_app() and s.github_app_installation_id),
        'app_slug': s.github_app_slug or 'planebyte-intent-radar',
        'redirect_uri': s.github_oauth_redirect_uri,
        'status': 'NOT_CONNECTED',
        'installation_id': None,
        'account_login': None,
        'account_type': None,
        'permissions': {},
        'repositories': [],
        'last_verified_at': None,
        'last_error_code': None,
        'revision': 0,
    }
    if not row:
        return base
    return {
        **base,
        'connection_id': row['id'],
        'status': row['status'],
        'installation_id': row['installation_id'],
        'account_login': row['account_login'],
        'account_type': row['account_type'],
        'permissions': json.loads(row['permissions_json'] or '{}'),
        'repositories': json.loads(row['repositories_json'] or '[]'),
        'last_verified_at': row['last_verified_at'],
        'last_error_code': row['last_error_code'],
        'revision': row['revision'],
    }


def start_oauth(c) -> dict:
    ctx = context(c, True, True)
    s = get_settings()
    if not _oauth_configured():
        raise HTTPException(503, 'GitHub customer OAuth is not configured on the server.')
    row = c.execute('SELECT * FROM intent_github_connections WHERE organization_id=?', (ctx.organization_id,)).fetchone()
    if row:
        conn_id, rev = row['id'], row['revision']
        if row['status'] in ('DISCONNECTED', 'REVOKED', 'REAUTH_REQUIRED'):
            c.execute("UPDATE intent_github_connections SET status='PENDING', updated_at=? WHERE id=? AND organization_id=?", (now(), conn_id, ctx.organization_id))
    else:
        conn_id, rev = str(uuid.uuid4()), 1
        c.execute(
            "INSERT INTO intent_github_connections(id,organization_id,owner_user_id,status,permissions_json,repositories_json,revision,created_at,updated_at) VALUES(?,?,?,'PENDING','{}','[]',1,?,?)",
            (conn_id, ctx.organization_id, ctx.actor, now(), now()),
        )
    # Expire/cancel any stale pending OAuth states for this workspace
    c.execute("UPDATE intent_github_oauth_states SET status='CANCELLED' WHERE organization_id=? AND status='PENDING'", (ctx.organization_id,))
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(48)
    state_hash = hashlib.sha256(state.encode('ascii')).hexdigest()
    sealed_verifier = seal({'verifier': verifier}, organization_id=ctx.organization_id, connection_id=conn_id, provider='github', purpose='OAUTH_PKCE')
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
    c.execute(
        "INSERT INTO intent_github_oauth_states(state_hash,organization_id,connection_id,actor,connection_revision,verifier_ciphertext,status,expires_at,created_at) VALUES(?,?,?,?,?,?,'PENDING',?,?)",
        (state_hash, ctx.organization_id, conn_id, ctx.actor, rev, sealed_verifier, expires_at, now()),
    )
    params = {
        'client_id': s.github_app_client_id,
        'redirect_uri': s.github_oauth_redirect_uri,
        'state': state,
        'code_challenge': _pkce_challenge(verifier),
        'code_challenge_method': 'S256',
    }
    authorize_url = 'https://github.com/login/oauth/authorize?' + urlencode(params)
    install_url = f"https://github.com/apps/{s.github_app_slug or 'planebyte-intent-radar'}/installations/new?state={state}"
    from app.intent_radar.service import audit
    audit(c, 'GITHUB_OAUTH_STARTED', conn_id)
    return {
        'authorize_url': authorize_url,
        'install_url': install_url,
        'expires_at': expires_at,
        'redirect_uri': s.github_oauth_redirect_uri,
    }


async def complete_oauth(c, *, code: str, state: str, installation_id: str | None = None) -> dict:
    ctx = context(c, True, True)
    s = get_settings()
    if not _oauth_configured():
        raise HTTPException(503, 'GitHub customer OAuth is not configured on the server.')
    if not code or not state or len(code) > 256 or len(state) > 256:
        raise HTTPException(422, 'Valid GitHub authorization code and state are required.')
    state_hash = hashlib.sha256(state.encode('ascii')).hexdigest()
    lease = str(uuid.uuid4())
    lease_until = (datetime.now(timezone.utc) + timedelta(seconds=60)).isoformat()
    claimed = c.execute(
        "UPDATE intent_github_oauth_states SET status='PROCESSING', lease_owner=?, lease_until=? WHERE state_hash=? AND organization_id=? AND actor=? AND status='PENDING' AND expires_at>?",
        (lease, lease_until, state_hash, ctx.organization_id, ctx.actor, now()),
    ).rowcount
    if not claimed:
        raise HTTPException(409, 'GitHub OAuth state is invalid, expired, or already used.')
    state_row = c.execute('SELECT * FROM intent_github_oauth_states WHERE state_hash=?', (state_hash,)).fetchone()
    conn_id = state_row['connection_id']
    verifier = open_envelope(state_row['verifier_ciphertext'], organization_id=ctx.organization_id, connection_id=conn_id, provider='github', purpose='OAUTH_PKCE')['verifier']
    c.commit()
    try:
        oauth_client = JsonClient('https://github.com', headers={'Accept': 'application/json'})
        token_resp = await oauth_client.request(
            '/login/oauth/access_token',
            method='POST',
            body={
                'client_id': s.github_app_client_id,
                'client_secret': s.github_app_client_secret.get_secret_value(),
                'code': code,
                'redirect_uri': s.github_oauth_redirect_uri,
                'code_verifier': verifier,
            },
        )
        access_token = token_resp.get('access_token')
        if not access_token:
            raise HTTPException(400, 'GitHub rejected the authorization code: ' + str(token_resp.get('error_description') or token_resp.get('error') or 'unknown error'))
        user_client = JsonClient(
            'https://api.github.com',
            headers={'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': s.github_api_version, 'Authorization': 'Bearer ' + access_token},
        )
        user_info = await user_client.request('/user')
        inst_resp = await user_client.request('/user/installations', params={'per_page': 50})
        installations = inst_resp.get('installations') or []
        chosen = None
        if installation_id and str(installation_id).isdigit():
            chosen = next((i for i in installations if str(i.get('id')) == str(installation_id)), None)
            if not chosen:
                raise HTTPException(403, 'The requested GitHub installation is not authorized by your GitHub account.')
        elif installations:
            chosen = installations[0]
        if not chosen:
            raise HTTPException(409, 'No GitHub App installation found on this GitHub account. Install the PlaneByte Intent Radar GitHub App first.')
        chosen_id = str(chosen['id'])
        repos_resp = await user_client.request(f'/user/installations/{chosen_id}/repositories', params={'per_page': 100})
        repos = [
            {'id': r['id'], 'full_name': r['full_name'], 'private': bool(r.get('private')), 'selected': True}
            for r in (repos_resp.get('repositories') or [])[:100]
            if isinstance(r.get('id'), int) and r.get('full_name')
        ]
        expires_in = token_resp.get('expires_in')
        refresh_expires_in = token_resp.get('refresh_token_expires_in')
        creds_payload = {
            'access_token': access_token,
            'refresh_token': token_resp.get('refresh_token'),
            'token_type': token_resp.get('token_type', 'bearer'),
            'expires_at': (datetime.now(timezone.utc) + timedelta(seconds=int(expires_in))).isoformat() if expires_in else None,
            'refresh_expires_at': (datetime.now(timezone.utc) + timedelta(seconds=int(refresh_expires_in))).isoformat() if refresh_expires_in else None,
        }
        sealed_creds = seal(creds_payload, organization_id=ctx.organization_id, connection_id=conn_id, provider='github', purpose='CREDENTIALS')
        account = chosen.get('account') or {}
        c.execute(
            """UPDATE intent_github_connections
               SET installation_id=?, github_user_id=?, account_login=?, account_type=?, status='CONNECTED',
                   permissions_json=?, repositories_json=?, credentials_ciphertext=?,
                   revision=revision+1, last_verified_at=?, last_error_code=NULL, updated_at=?
               WHERE id=? AND organization_id=?""",
            (
                chosen_id,
                str(user_info.get('id') or ''),
                str(account.get('login') or user_info.get('login') or ''),
                str(account.get('type') or 'User'),
                json.dumps(chosen.get('permissions') or {}),
                json.dumps(repos),
                sealed_creds,
                now(),
                now(),
                conn_id,
                ctx.organization_id,
            ),
        )
        c.execute("UPDATE intent_github_oauth_states SET status='CONSUMED' WHERE state_hash=? AND lease_owner=?", (state_hash, lease))
        from app.intent_radar.service import audit
        audit(c, 'GITHUB_CONNECTED', conn_id)
        c.commit()
        return connection_status(c)
    except Exception:
        c.execute("UPDATE intent_github_oauth_states SET status='CANCELLED' WHERE state_hash=? AND lease_owner=?", (state_hash, lease))
        c.commit()
        raise


def update_repositories(c, repository_ids: list[int]) -> dict:
    ctx = context(c, True, True)
    row = c.execute('SELECT * FROM intent_github_connections WHERE organization_id=?', (ctx.organization_id,)).fetchone()
    if not row or row['status'] != 'CONNECTED':
        raise HTTPException(409, 'Connect a GitHub installation before selecting repositories.')
    existing = json.loads(row['repositories_json'] or '[]')
    allowed_ids = {r['id'] for r in existing if isinstance(r.get('id'), int)}
    chosen = set(repository_ids or [])
    if not chosen.issubset(allowed_ids):
        raise HTTPException(403, 'Repository selection contains repositories outside the authorized installation.')
    updated = [{**r, 'selected': r['id'] in chosen} for r in existing]
    c.execute(
        'UPDATE intent_github_connections SET repositories_json=?, revision=revision+1, updated_at=? WHERE id=? AND organization_id=?',
        (json.dumps(updated), now(), row['id'], ctx.organization_id),
    )
    GitHubAuth.revoke_cached()
    from app.intent_radar.service import audit
    audit(c, 'GITHUB_REPOSITORIES_UPDATED', row['id'])
    return connection_status(c)


async def refresh_user_token(c, org_id: str) -> str | None:
    """Refresh expiring GitHub user OAuth token; marks REAUTH_REQUIRED on failure."""
    s = get_settings()
    row = c.execute('SELECT * FROM intent_github_connections WHERE organization_id=?', (org_id,)).fetchone()
    if not row or row['status'] != 'CONNECTED' or not row['credentials_ciphertext']:
        return None
    creds = open_envelope(row['credentials_ciphertext'], organization_id=org_id, connection_id=row['id'], provider='github', purpose='CREDENTIALS')
    exp = creds.get('expires_at')
    if exp and exp > (datetime.now(timezone.utc) + timedelta(minutes=2)).isoformat():
        return creds.get('access_token')
    refresh_token = creds.get('refresh_token')
    if not refresh_token or not _oauth_configured():
        return creds.get('access_token')
    try:
        oauth_client = JsonClient('https://github.com', headers={'Accept': 'application/json'})
        resp = await oauth_client.request(
            '/login/oauth/access_token',
            method='POST',
            body={
                'client_id': s.github_app_client_id,
                'client_secret': s.github_app_client_secret.get_secret_value(),
                'grant_type': 'refresh_token',
                'refresh_token': refresh_token,
            },
        )
        new_token = resp.get('access_token')
        if not new_token:
            raise ProviderFailure('GITHUB_REFRESH_FAILED')
        new_creds = {
            **creds,
            'access_token': new_token,
            'refresh_token': resp.get('refresh_token') or refresh_token,
            'expires_at': (datetime.now(timezone.utc) + timedelta(seconds=int(resp['expires_in']))).isoformat() if resp.get('expires_in') else None,
        }
        sealed = seal(new_creds, organization_id=org_id, connection_id=row['id'], provider='github', purpose='CREDENTIALS')
        c.execute('UPDATE intent_github_connections SET credentials_ciphertext=?, last_verified_at=?, updated_at=? WHERE id=? AND organization_id=?', (sealed, now(), now(), row['id'], org_id))
        c.commit()
        return new_token
    except Exception:
        c.execute("UPDATE intent_github_connections SET status='REAUTH_REQUIRED', last_error_code='TOKEN_REFRESH_FAILED', updated_at=? WHERE id=? AND organization_id=?", (now(), row['id'], org_id))
        c.commit()
        return None


def disconnect(c) -> dict:
    ctx = context(c, True, True)
    row = c.execute('SELECT * FROM intent_github_connections WHERE organization_id=?', (ctx.organization_id,)).fetchone()
    if not row:
        return connection_status(c)
    c.execute(
        "UPDATE intent_github_connections SET status='DISCONNECTED', credentials_ciphertext=NULL, installation_id=NULL, repositories_json='[]', permissions_json='{}', revision=revision+1, updated_at=? WHERE id=? AND organization_id=?",
        (now(), row['id'], ctx.organization_id),
    )
    c.execute("UPDATE intent_github_oauth_states SET status='CANCELLED' WHERE organization_id=? AND status IN ('PENDING','PROCESSING')", (ctx.organization_id,))
    GitHubAuth.revoke_cached()
    from app.intent_radar.service import audit
    audit(c, 'GITHUB_DISCONNECTED', row['id'])
    return connection_status(c)


MAX_WEBHOOK_BYTES = 512_000
MAX_WEBHOOK_ATTEMPTS = 3


def verify_webhook_signature(raw_body: bytes, signature_header: str) -> bool:
    secret = get_settings().github_app_webhook_secret.get_secret_value()
    if not secret or not signature_header or not signature_header.startswith('sha256='):
        return False
    expected = 'sha256=' + hmac.new(secret.encode('utf-8'), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header.strip())


def ingest_webhook(c, *, raw_body: bytes, delivery_id: str, event_type: str, signature: str) -> dict:
    s = get_settings()
    if not s.github_app_webhook_secret.get_secret_value():
        raise HTTPException(503, 'GitHub webhooks are not configured.')
    if len(raw_body) > MAX_WEBHOOK_BYTES:
        raise HTTPException(413, 'Webhook payload exceeds supported size.')
    if not delivery_id or len(delivery_id) > 128 or not event_type or len(event_type) > 80:
        raise HTTPException(400, 'Missing required GitHub delivery metadata.')
    if not verify_webhook_signature(raw_body, signature):
        logger.warning('Rejected GitHub webhook with invalid signature (event=%s delivery=%s)', event_type, delivery_id)
        raise HTTPException(401, 'Invalid GitHub webhook signature.')
    if not s.intent_radar_github_webhooks_enabled:
        logger.info('Verified GitHub webhook signature while processing disabled (event=%s delivery=%s)', event_type, delivery_id)
        raise HTTPException(503, 'GitHub webhook processing is currently disabled.')
    try:
        payload = json.loads(raw_body.decode('utf-8'))
    except (UnicodeDecodeError, ValueError):
        raise HTTPException(400, 'Invalid JSON webhook payload.') from None
    payload_hash = hashlib.sha256(raw_body).hexdigest()
    installation = payload.get('installation') or {}
    inst_id = str(installation.get('id')) if installation.get('id') is not None else None
    conn = c.execute("SELECT id,organization_id FROM intent_github_connections WHERE installation_id=? AND status IN ('CONNECTED','PENDING','REAUTH_REQUIRED')", (inst_id,)).fetchone() if inst_id else None
    org_id = conn['organization_id'] if conn else None
    conn_id = conn['id'] if conn else None
    event_id = str(uuid.uuid4())
    sealed_payload = seal(payload, organization_id=org_id or 'system', connection_id=delivery_id, provider='github', purpose='WEBHOOK_EVENT')
    inserted = c.execute(
        """INSERT INTO intent_provider_events(id,provider,delivery_id,organization_id,connection_id,installation_id,event_type,payload_hash,payload_ciphertext,status,attempts,created_at,updated_at)
           VALUES(?, 'github', ?, ?, ?, ?, ?, ?, ?, 'QUEUED', 0, ?, ?)
           ON CONFLICT DO NOTHING""",
        (event_id, delivery_id, org_id, conn_id, inst_id, event_type, payload_hash, sealed_payload, now(), now()),
    ).rowcount
    if not inserted:
        return {'status': 'DUPLICATE', 'delivery_id': delivery_id}
    c.commit()
    processed = process_github_event(c, event_id)
    logger.info('Processed GitHub webhook (event=%s delivery=%s status=%s)', event_type, delivery_id, processed)
    return {'status': processed, 'delivery_id': delivery_id, 'event_id': event_id}


def _repo_authorized_for_connection(conn, payload: dict) -> bool:
    if not conn or conn['status'] != 'CONNECTED':
        return False
    repos = json.loads(conn['repositories_json'] or '[]')
    if not repos:
        # Installation has no explicit per-repo restriction saved yet; public/all-repo scope permitted.
        return True
    repo_obj = payload.get('repository') or {}
    repo_id = repo_obj.get('id')
    repo_name = (repo_obj.get('full_name') or '').casefold()
    selected = [r for r in repos if r.get('selected', True)]
    for entry in selected:
        if repo_id is not None and entry.get('id') == repo_id:
            return True
        if repo_name and (entry.get('full_name') or '').casefold() == repo_name:
            return True
    return False


def process_github_event(c, event_id: str) -> str:
    row = c.execute("SELECT * FROM intent_provider_events WHERE id=? AND provider='github'", (event_id,)).fetchone()
    if not row or row['status'] in ('COMPLETE', 'IGNORED'):
        return row['status'] if row else 'IGNORED'
    if (row['attempts'] or 0) >= MAX_WEBHOOK_ATTEMPTS:
        return 'FAILED'
    payload = open_envelope(row['payload_ciphertext'], organization_id=row['organization_id'] or 'system', connection_id=row['delivery_id'], provider='github', purpose='WEBHOOK_EVENT')
    event_type = row['event_type']
    action = str(payload.get('action') or '')
    inst_id = row['installation_id']
    try:
        if event_type == 'installation' and action in ('deleted', 'suspend') and inst_id:
            c.execute(
                "UPDATE intent_github_connections SET status='REVOKED', credentials_ciphertext=NULL, last_error_code=?, revision=revision+1, updated_at=? WHERE installation_id=?",
                ('INSTALLATION_' + action.upper(), now(), inst_id),
            )
            GitHubAuth.revoke_cached()
            status = 'COMPLETE'
        elif event_type == 'installation_repositories' and inst_id and row['organization_id']:
            conn = c.execute('SELECT * FROM intent_github_connections WHERE organization_id=? AND installation_id=?', (row['organization_id'], inst_id)).fetchone()
            if conn:
                repos = json.loads(conn['repositories_json'] or '[]')
                removed_ids = {r.get('id') for r in payload.get('repositories_removed') or []}
                repos = [r for r in repos if r.get('id') not in removed_ids]
                existing_ids = {r.get('id') for r in repos}
                for added in payload.get('repositories_added') or []:
                    if added.get('id') and added['id'] not in existing_ids:
                        repos.append({'id': added['id'], 'full_name': added.get('full_name', ''), 'private': bool(added.get('private')), 'selected': True})
                c.execute('UPDATE intent_github_connections SET repositories_json=?, revision=revision+1, updated_at=? WHERE id=?', (json.dumps(repos[:100]), now(), conn['id']))
                GitHubAuth.revoke_cached()
            status = 'COMPLETE'
        elif event_type in ('issues', 'issue_comment', 'discussion', 'discussion_comment', 'release', 'pull_request') and row['organization_id'] and inst_id:
            conn = c.execute(
                "SELECT id,status,repositories_json FROM intent_github_connections WHERE organization_id=? AND installation_id=?",
                (row['organization_id'], inst_id),
            ).fetchone()
            if not _repo_authorized_for_connection(conn, payload):
                status = 'IGNORED'
            else:
                record = _normalize_webhook_record(event_type, payload)
                if record:
                    _persist_webhook_signal(c, row['organization_id'], record)
                    status = 'COMPLETE'
                else:
                    status = 'IGNORED'
        else:
            status = 'IGNORED'
        c.execute('UPDATE intent_provider_events SET status=?, attempts=attempts+1, updated_at=? WHERE id=?', (status, now(), event_id))
        c.commit()
        return status
    except Exception as exc:
        logger.warning('Failed processing GitHub webhook (event=%s delivery=%s error=%s)', event_type, row['delivery_id'], type(exc).__name__)
        c.execute("UPDATE intent_provider_events SET status='FAILED', attempts=attempts+1, error_code=?, updated_at=? WHERE id=?", (type(exc).__name__, now(), event_id))
        c.commit()
        return 'FAILED'


ALLOWED_WEBHOOK_ACTIONS: dict[str, set[str]] = {
    'issues': {'opened', 'edited', 'reopened', ''},
    'issue_comment': {'created', 'edited', ''},
    'discussion': {'created', 'edited', ''},
    'discussion_comment': {'created', 'edited', ''},
    'release': {'published', 'released', 'edited', ''},
    'pull_request': {'opened', 'edited', 'reopened', 'ready_for_review', ''},
}


def _normalize_webhook_record(event_type: str, payload: dict) -> dict | None:
    action = str(payload.get('action') or '').strip().lower()
    allowed_actions = ALLOWED_WEBHOOK_ACTIONS.get(event_type)
    if allowed_actions is None or action not in allowed_actions:
        return None
    repo_obj = payload.get('repository') or {}
    repo = str(repo_obj.get('full_name') or '').strip()
    is_private = bool(repo_obj.get('private'))
    visibility = 'private_connected' if is_private else 'public'
    if event_type == 'issues' and isinstance(payload.get('issue'), dict):
        it = payload['issue']
        if not it.get('id'):
            return None
        return connectors.normalized(
            'GitHub', f"issue:{it.get('id')}", it.get('html_url', ''), it.get('title', ''), it.get('body') or '', it.get('created_at') or it.get('updated_at') or now(),
            fetch_method='github_webhook', content_kind='issue', repo=repo, visibility=visibility,
            attribution={'author': providers.text((it.get('user') or {}).get('login'), 100), 'profile_url': (it.get('user') or {}).get('html_url'), 'license': 'GitHub API', 'source': 'GitHub'},
            tags=[lb.get('name', '') for lb in (it.get('labels') or []) if isinstance(lb, dict) and lb.get('name')][:10],
        )
    if event_type == 'issue_comment' and isinstance(payload.get('comment'), dict) and isinstance(payload.get('issue'), dict):
        cm, it = payload['comment'], payload['issue']
        if not cm.get('id'):
            return None
        title = it.get('title') or (f"Comment on {repo}#{it.get('number')}" if repo and it.get('number') else 'GitHub issue comment')
        return connectors.normalized(
            'GitHub', f"issue_comment:{cm.get('id')}", cm.get('html_url', ''), title, cm.get('body') or '', cm.get('created_at') or cm.get('updated_at') or now(),
            fetch_method='github_webhook', content_kind='comment', repo=repo, visibility=visibility, parent_id=str(it.get('id') or ''),
            attribution={'author': providers.text((cm.get('user') or {}).get('login'), 100), 'profile_url': (cm.get('user') or {}).get('html_url'), 'license': 'GitHub API', 'source': 'GitHub'},
        )
    if event_type == 'discussion' and isinstance(payload.get('discussion'), dict):
        ds = payload['discussion']
        if not ds.get('id'):
            return None
        return connectors.normalized(
            'GitHub', f"discussion:{ds.get('id')}", ds.get('html_url', ''), ds.get('title', ''), ds.get('body') or '', ds.get('created_at') or ds.get('updated_at') or now(),
            fetch_method='github_webhook', content_kind='discussion', repo=repo, visibility=visibility,
            attribution={'author': providers.text((ds.get('user') or {}).get('login'), 100), 'profile_url': (ds.get('user') or {}).get('html_url'), 'license': 'GitHub API', 'source': 'GitHub'},
        )
    if event_type == 'discussion_comment' and isinstance(payload.get('comment'), dict) and isinstance(payload.get('discussion'), dict):
        cm, ds = payload['comment'], payload['discussion']
        if not cm.get('id'):
            return None
        title = ds.get('title') or (f"Discussion comment in {repo}" if repo else 'GitHub discussion comment')
        return connectors.normalized(
            'GitHub', f"discussion_comment:{cm.get('id')}", cm.get('html_url', ''), title, cm.get('body') or '', cm.get('created_at') or cm.get('updated_at') or now(),
            fetch_method='github_webhook', content_kind='comment', repo=repo, visibility=visibility, parent_id=str(ds.get('id') or ''),
            attribution={'author': providers.text((cm.get('user') or {}).get('login'), 100), 'profile_url': (cm.get('user') or {}).get('html_url'), 'license': 'GitHub API', 'source': 'GitHub'},
        )
    if event_type == 'release' and isinstance(payload.get('release'), dict):
        rl = payload['release']
        if not rl.get('id'):
            return None
        rel_name = rl.get('name') or rl.get('tag_name') or 'release'
        title = f"{repo} {rel_name}".strip() if repo else rel_name
        return connectors.normalized(
            'GitHub', f"release:{rl.get('id')}", rl.get('html_url', ''), title, rl.get('body') or rel_name, rl.get('published_at') or rl.get('created_at') or now(),
            fetch_method='github_webhook', content_kind='release', repo=repo, visibility=visibility,
            attribution={'author': providers.text((rl.get('author') or {}).get('login'), 100), 'profile_url': (rl.get('author') or {}).get('html_url'), 'license': 'GitHub API', 'source': 'GitHub'},
        )
    if event_type == 'pull_request' and isinstance(payload.get('pull_request'), dict):
        pr = payload['pull_request']
        if not pr.get('id'):
            return None
        return connectors.normalized(
            'GitHub', f"pull_request:{pr.get('id')}", pr.get('html_url', ''), pr.get('title', ''), pr.get('body') or '', pr.get('created_at') or pr.get('updated_at') or now(),
            fetch_method='github_webhook', content_kind='pull_request', repo=repo, visibility=visibility,
            attribution={'author': providers.text((pr.get('user') or {}).get('login'), 100), 'profile_url': (pr.get('user') or {}).get('html_url'), 'license': 'GitHub API', 'source': 'GitHub'},
        )
    return None


def _persist_webhook_signal(c, organization_id: str, raw: dict) -> int:
    from app.intent_radar import models, classification
    monitors = c.execute("SELECT id,created_by,configuration_json FROM intent_monitors WHERE organization_id=? AND status='Active'", (organization_id,)).fetchall()
    matched_count = 0
    for m in monitors:
        cfg = json.loads(m['configuration_json'])
        if 'github' not in (cfg.get('sources') or []):
            continue
        query = models.Search.model_validate(cfg)
        repo = (raw.get('provenance') or {}).get('repo') or ''
        if query.github_repos and (not repo or repo.casefold() not in {r.casefold() for r in query.github_repos}):
            continue
        item = classification.classify(raw, query)
        if not item:
            continue
        item['evidence'].update(provenance=raw.get('provenance', {}), content_fingerprint=raw.get('content_fingerprint'), search_configuration=cfg)
        signal_id = str(uuid.uuid5(uuid.NAMESPACE_URL, organization_id + ':GitHub:' + item['source_record_id']))
        c.execute(
            'INSERT INTO intent_signals(id,organization_id,source,source_record_id,source_url,title,excerpt,observed_at,retrieved_at,category,score,evidence_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(organization_id,source,source_record_id) DO NOTHING',
            (signal_id, organization_id, item['source'], item['source_record_id'], item['source_url'], item['title'], item['excerpt'], item['observed_at'], item['retrieved_at'], item['category'], item['score'], json.dumps(item['evidence'])),
        )
        linked = c.execute('INSERT INTO intent_monitor_signals(organization_id,monitor_id,signal_id,matched_at) VALUES(?,?,?,?) ON CONFLICT(organization_id,monitor_id,signal_id) DO NOTHING', (organization_id, m['id'], signal_id, now())).rowcount
        matched_count += 1
        if linked:
            alert_id = str(uuid.uuid5(uuid.NAMESPACE_URL, organization_id + ':intent-alert:match:' + m['id'] + ':' + signal_id))
            inserted_alert = c.execute(
                'INSERT INTO intent_alerts(id,organization_id,monitor_id,signal_id,event_key,title,description,created_at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(organization_id,event_key) DO NOTHING',
                (alert_id, organization_id, m['id'], signal_id, 'match:' + m['id'] + ':' + signal_id, 'GitHub webhook matched monitor', item['title'][:200], now()),
            ).rowcount
            if inserted_alert and m['created_by']:
                c.execute('INSERT INTO workspace_notifications(id,organization_id,user_id,kind,entity_id,created_at) VALUES(?,?,?,?,?,?)', (str(uuid.uuid4()), organization_id, m['created_by'], 'INTENT_RADAR', alert_id, now()))
    return matched_count


class GitHubCollector:
    async def fetch(self, c, q, permit):
        org = context(c).organization_id
        s = get_settings()
        if not (s.intent_radar_github_enabled and _configured_app()):
            raise connectors.SourceUnavailable('GITHUB_NOT_CONFIGURED')
        use_connected = q.github_scope == 'connected'
        auth = GitHubAuth(permit=permit)
        allowed_repos: list[str] = []
        if use_connected:
            row = c.execute("SELECT * FROM intent_github_connections WHERE organization_id=? AND status='CONNECTED'", (org,)).fetchone()
            if not row or not row['installation_id']:
                raise connectors.SourceUnavailable('GITHUB_CONNECTION_REQUIRED')
            selected = [r for r in json.loads(row['repositories_json'] or '[]') if r.get('selected', True)]
            repo_ids = [r['id'] for r in selected if isinstance(r.get('id'), int)][:100]
            allowed_repos = [r['full_name'] for r in selected if r.get('full_name')]
            token = await auth.token(row['installation_id'], repository_ids=repo_ids or None)
            scope_public = False
            scope_tag = 'gh:' + row['id']
        else:
            if not s.intent_radar_github_public_search_enabled or not s.github_app_installation_id:
                raise connectors.SourceUnavailable('GITHUB_PUBLIC_SEARCH_DISABLED')
            token = await auth.token(s.github_app_installation_id)
            scope_public = True
            scope_tag = ''

        gw = Gateway(
            c, 'github', 'https://api.github.com', permit,
            headers={'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': s.github_api_version, 'Authorization': 'Bearer ' + token},
            public=scope_public, scope_tag=scope_tag, seconds=26, max_requests=24,
        )
        repos = _sanitize_repos(q.github_repos) if q.github_repos else []
        if use_connected and repos:
            allowed_set = {r.casefold() for r in allowed_repos}
            repos = [r for r in repos if r.casefold() in allowed_set]
            if not repos:
                raise connectors.SourceUnavailable('GITHUB_REPO_NOT_AUTHORIZED')
        if use_connected and not repos:
            repos = allowed_repos[:3]

        kw = ' '.join(q.keywords[:4])
        date_filter = ''
        if q.from_date:
            date_filter += f' created:>={q.from_date.isoformat()}'
        if q.to_date:
            date_filter += f' created:<={q.to_date.isoformat()}'
        since_cursor = q._collection_cursor.get('since')
        if since_cursor and not q.from_date:
            date_filter += f' updated:>={since_cursor[:10]}'

        visibility_q = ' is:public' if scope_public else ''
        repo_q = (' ' + ' '.join(f'repo:{r}' for r in repos[:3])) if repos else ''
        kinds = list(q.github_kinds or ['issues', 'discussions'])
        per_kind = max(3, min(10, q.result_limit // max(1, len(kinds))))
        items = []
        seen_ids = set(q._collection_cursor.get('seen_ids') or [])
        newest = since_cursor or ''
        vis_label = 'public' if scope_public else 'private_connected'

        if 'repositories' in kinds:
            data = await gw.request('/search/repositories', params={'q': f'{kw}{visibility_q} in:name,description', 'sort': 'updated', 'order': 'desc', 'per_page': per_kind}, ttl=600, bucket='search', capacity=30)
            for r in (data.get('items') or [])[:per_kind]:
                full_name = r.get('full_name') or ''
                rec_id = f"repo:{r.get('id')}"
                if rec_id in seen_ids:
                    continue
                ts = r.get('updated_at') or r.get('created_at')
                item = connectors.normalized(
                    'GitHub', rec_id, r.get('html_url', ''), full_name, r.get('description') or full_name, ts,
                    fetch_method='official_api', content_kind='repository', repo=full_name, visibility=vis_label,
                    tags=[t for t in (r.get('topics') or [])[:10] if t],
                    metrics={'stars': int(r.get('stargazers_count') or 0), 'open_issues': int(r.get('open_issues_count') or 0)},
                    attribution={'author': providers.text((r.get('owner') or {}).get('login'), 100), 'profile_url': (r.get('owner') or {}).get('html_url'), 'license': (r.get('license') or {}).get('spdx_id') or 'GitHub API', 'source': 'GitHub'},
                )
                if item:
                    items.append(item)
                    newest = max(newest, item['observed_at'])

        for kind, qual, content_kind in (('issues', 'is:issue', 'issue'), ('pull_requests', 'is:pr', 'pull_request')):
            if kind not in kinds:
                continue
            search_q = f'{kw} {qual}{visibility_q}{repo_q}{date_filter}'.strip()
            data = await gw.request('/search/issues', params={'q': search_q, 'sort': 'updated', 'order': 'desc', 'per_page': per_kind}, ttl=300, bucket='search', capacity=30)
            for it in (data.get('items') or [])[:per_kind]:
                rec_id = f"{content_kind}:{it.get('id')}"
                repo_url = it.get('repository_url') or ''
                repo_name = '/'.join(repo_url.rstrip('/').split('/')[-2:]) if '/repos/' in repo_url else ''
                ts = it.get('created_at') or it.get('updated_at')
                if rec_id not in seen_ids:
                    item = connectors.normalized(
                        'GitHub', rec_id, it.get('html_url', ''), it.get('title', ''), it.get('body') or it.get('title', ''), ts,
                        fetch_method='official_api', content_kind=content_kind, repo=repo_name, visibility=vis_label,
                        updated_at=it.get('updated_at'),
                        tags=[lb.get('name', '') for lb in (it.get('labels') or []) if lb.get('name')][:10],
                        metrics={'comments': int(it.get('comments') or 0)},
                        attribution={'author': providers.text((it.get('user') or {}).get('login'), 100), 'profile_url': (it.get('user') or {}).get('html_url'), 'license': 'GitHub API', 'source': 'GitHub'},
                    )
                    if item:
                        items.append(item)
                        newest = max(newest, item['observed_at'])
                if q.github_comments and kind == 'issues' and repo_name and it.get('number') and (it.get('comments') or 0) > 0 and gw.client.requests < 16:
                    try:
                        cmts = await gw.request(f"/repos/{repo_name}/issues/{it['number']}/comments", params={'per_page': 2}, ttl=300, bucket='core', capacity=5000)
                        for cm in (cmts if isinstance(cmts, list) else [])[:2]:
                            cm_id = f"issue_comment:{cm.get('id')}"
                            if cm_id in seen_ids:
                                continue
                            c_item = connectors.normalized(
                                'GitHub', cm_id, cm.get('html_url', ''), it.get('title', ''), cm.get('body') or '', cm.get('created_at'),
                                fetch_method='official_api', content_kind='comment', repo=repo_name, visibility=vis_label, parent_id=rec_id,
                                attribution={'author': providers.text((cm.get('user') or {}).get('login'), 100), 'profile_url': (cm.get('user') or {}).get('html_url'), 'license': 'GitHub API', 'source': 'GitHub'},
                            )
                            if c_item:
                                c_item['discussion_id'] = rec_id
                                items.append(c_item)
                    except ProviderFailure:
                        pass

        if 'discussions' in kinds and gw.client.requests < 18:
            gql_search = f'{kw}{repo_q}'.strip()
            gql_query = (
                'query($q: String!, $first: Int!) { search(query: $q, type: DISCUSSION, first: $first) { '
                'nodes { ... on Discussion { id url title bodyText createdAt updatedAt repository { nameWithOwner isPrivate } '
                'author { login url } category { name } comments(first: 2) { totalCount nodes { id url bodyText createdAt author { login url } } } } } } }'
            )
            try:
                gql = await gw.request('/graphql', method='POST', body={'query': gql_query, 'variables': {'q': gql_search, 'first': min(6, per_kind)}}, ttl=300, bucket='core', capacity=5000)
                nodes = ((gql.get('data') or {}).get('search') or {}).get('nodes') or []
                for node in nodes:
                    if not isinstance(node, dict) or not node.get('id'):
                        continue
                    repo_info = node.get('repository') or {}
                    if scope_public and repo_info.get('isPrivate'):
                        continue
                    rec_id = f"discussion:{node['id']}"
                    repo_name = repo_info.get('nameWithOwner') or ''
                    if rec_id not in seen_ids:
                        author = node.get('author') or {}
                        item = connectors.normalized(
                            'GitHub', rec_id, node.get('url', ''), node.get('title', ''), node.get('bodyText') or node.get('title', ''), node.get('createdAt'),
                            fetch_method='official_graphql', content_kind='discussion', repo=repo_name, visibility=vis_label,
                            updated_at=node.get('updatedAt'),
                            categories=[node['category']['name']] if (node.get('category') or {}).get('name') else [],
                            metrics={'comments': int((node.get('comments') or {}).get('totalCount') or 0)},
                            attribution={'author': providers.text(author.get('login'), 100), 'profile_url': author.get('url'), 'license': 'GitHub GraphQL API', 'source': 'GitHub'},
                        )
                        if item:
                            items.append(item)
                            newest = max(newest, item['observed_at'])
                    if q.github_comments:
                        for reply in ((node.get('comments') or {}).get('nodes') or [])[:2]:
                            r_id = f"discussion_comment:{reply.get('id')}"
                            if r_id in seen_ids or not reply.get('url'):
                                continue
                            r_author = reply.get('author') or {}
                            r_item = connectors.normalized(
                                'GitHub', r_id, reply.get('url', ''), node.get('title', ''), reply.get('bodyText') or '', reply.get('createdAt'),
                                fetch_method='official_graphql', content_kind='comment', repo=repo_name, visibility=vis_label, parent_id=rec_id,
                                attribution={'author': providers.text(r_author.get('login'), 100), 'profile_url': r_author.get('url'), 'license': 'GitHub GraphQL API', 'source': 'GitHub'},
                            )
                            if r_item:
                                r_item['discussion_id'] = rec_id
                                items.append(r_item)
            except ProviderFailure:
                pass

        if 'releases' in kinds and repos and gw.client.requests < 20:
            for repo_name in repos[:3]:
                try:
                    rels = await gw.request(f'/repos/{repo_name}/releases', params={'per_page': 4}, ttl=600, bucket='core', capacity=5000)
                    for rl in (rels if isinstance(rels, list) else [])[:4]:
                        rec_id = f"release:{rl.get('id')}"
                        if rec_id in seen_ids:
                            continue
                        item = connectors.normalized(
                            'GitHub', rec_id, rl.get('html_url', ''), f"{repo_name} {rl.get('name') or rl.get('tag_name') or 'release'}", rl.get('body') or rl.get('name') or repo_name, rl.get('published_at') or rl.get('created_at'),
                            fetch_method='official_api', content_kind='release', repo=repo_name, visibility=vis_label,
                            attribution={'author': providers.text((rl.get('author') or {}).get('login'), 100), 'profile_url': (rl.get('author') or {}).get('html_url'), 'license': 'GitHub API', 'source': 'GitHub'},
                        )
                        if item:
                            items.append(item)
                            newest = max(newest, item['observed_at'])
                except ProviderFailure:
                    pass

        new_seen = list(dict.fromkeys([*(x['source_record_id'] for x in items), *seen_ids]))[:600]
        quota_rem = None
        if gw.client.last_headers.get('x-ratelimit-remaining', '').isdigit():
            quota_rem = int(gw.client.last_headers['x-ratelimit-remaining'])
        return {
            'items': items[:q.result_limit],
            'requests': gw.client.requests,
            'scanned': len(items),
            'next_offset': None,
            'quota_remaining': quota_rem,
            'cursor': {'seen_ids': new_seen, 'since': newest or now()},
            'coverage': f"Official GitHub {'connected workspace' if use_connected else 'public'} API ({', '.join(kinds)}) with installation-token auth, caching ({gw.cache_hits} cache hit(s)) and incremental checkpoints.",
        }
