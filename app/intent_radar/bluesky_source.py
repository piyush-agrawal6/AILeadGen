"""Bluesky Public API adapter (api.bsky.app) and bounded Jetstream v2 WebSocket consumer."""
import asyncio, hashlib, json, time, uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from app.config.settings import get_settings
from app.database.connection import db_session
from app.database.prospects import now
from app.intent_radar import connectors, providers
from app.intent_radar.permissions import context
from app.intent_radar.source_http import ProviderFailure
from app.intent_radar.source_runtime import Gateway

STREAM_ID = 'bluesky:jetstream:v2'


def _post_url(uri: str, handle: str) -> str:
    # at://did:plc:xxx/app.bsky.feed.post/rkey -> https://bsky.app/profile/{handle}/post/{rkey}
    parts = str(uri or '').removeprefix('at://').split('/')
    actor = handle or (parts[0] if parts else '')
    rkey = parts[-1] if len(parts) >= 3 else ''
    if not actor or not rkey:
        return ''
    return f'https://bsky.app/profile/{actor}/post/{rkey}'


def _normalize_post(post: dict, *, parent_id: str | None = None, depth: int = 0) -> dict | None:
    uri = post.get('uri') or ''
    record = post.get('record') or {}
    author = post.get('author') or {}
    handle = author.get('handle') or author.get('did') or ''
    text_body = record.get('text') or ''
    created = record.get('createdAt') or post.get('indexedAt')
    url = _post_url(uri, handle)
    if not uri or not url or not text_body or not created:
        return None
    title = providers.text(text_body.splitlines()[0] if text_body else handle, 140)
    metrics = {
        k: int(post.get(src) or 0)
        for src, k in (('likeCount', 'likes'), ('repostCount', 'reposts'), ('replyCount', 'replies'))
        if post.get(src) is not None
    }
    return connectors.normalized(
        'Bluesky', uri, url, title, text_body, created,
        fetch_method='official_api', content_kind='post', author_handle=handle,
        parent_id=parent_id, depth=depth or None, metrics=metrics or None,
        attribution={'author': providers.text(author.get('displayName') or handle, 100), 'profile_url': f'https://bsky.app/profile/{handle}' if handle else None, 'license': 'Bluesky Public API', 'source': 'Bluesky'},
    )


class BlueskyCollector:
    async def fetch(self, c, q, permit):
        s = get_settings()
        if not s.intent_radar_bluesky_enabled:
            raise connectors.SourceUnavailable('BLUESKY_DISABLED')
        # Prefer working documented api.bsky.app (public.api.bsky.app returns 403 on searchPosts)
        preferred = (s.bluesky_api_base_url or 'https://api.bsky.app').rstrip('/')
        if preferred == 'https://public.api.bsky.app':
            preferred = 'https://api.bsky.app'
        gw = Gateway(c, 'bluesky', preferred, permit, public=True, seconds=25, max_requests=14)
        kw = ' '.join(q.keywords[:4])
        seen_ids = set(q._collection_cursor.get('seen_ids') or [])
        since = q._collection_cursor.get('since')
        if q.from_date:
            from_iso = q.from_date.isoformat() + 'T00:00:00Z'
            since = max(since, from_iso) if since else from_iso
        until = (q.to_date.isoformat() + 'T23:59:59Z') if q.to_date else None
        items = []
        newest = since or ''
        next_cursor = None

        if q.bluesky_mode == 'search':
            params = {'q': kw, 'limit': min(20, max(5, q.result_limit)), 'sort': 'latest'}
            if since:
                params['since'] = since
            if until:
                params['until'] = until
            if q.bluesky_handles:
                params['author'] = q.bluesky_handles[0].lstrip('@')
            if q.tags:
                params['tag'] = q.tags[:3]
            data = await gw.request('/xrpc/app.bsky.feed.searchPosts', params=params, ttl=180, bucket='search', capacity=60)
            next_cursor = data.get('cursor')
            for post in (data.get('posts') or [])[:q.result_limit]:
                uri = post.get('uri') or ''
                if uri in seen_ids:
                    continue
                norm = _normalize_post(post)
                if norm:
                    items.append(norm)
                    newest = max(newest, norm['observed_at'])
                if q.bluesky_threads and (post.get('replyCount') or 0) > 0 and gw.client.requests < 10:
                    try:
                        thread = await gw.request('/xrpc/app.bsky.feed.getPostThread', params={'uri': uri, 'depth': 1, 'parentHeight': 0}, ttl=180, bucket='core', capacity=120)
                        for rep in ((thread.get('thread') or {}).get('replies') or [])[:2]:
                            rpost = rep.get('post') if isinstance(rep, dict) else None
                            if not rpost or (rpost.get('uri') or '') in seen_ids:
                                continue
                            rnorm = _normalize_post(rpost, parent_id=uri, depth=1)
                            if rnorm:
                                rnorm['discussion_id'] = uri
                                items.append(rnorm)
                    except ProviderFailure:
                        pass

        elif q.bluesky_mode == 'feeds':
            handles = [h.lstrip('@') for h in (q.bluesky_handles or []) if h.strip()][:3]
            if not handles:
                actors = await gw.request('/xrpc/app.bsky.actor.searchActors', params={'q': kw, 'limit': 2}, ttl=600, bucket='core', capacity=120)
                handles = [a.get('handle') for a in (actors.get('actors') or []) if a.get('handle')][:2]
            for handle in handles:
                feed = await gw.request('/xrpc/app.bsky.feed.getAuthorFeed', params={'actor': handle, 'limit': 10}, ttl=180, bucket='core', capacity=120)
                for entry in (feed.get('feed') or [])[:10]:
                    post = entry.get('post') if isinstance(entry, dict) else None
                    if not post or (post.get('uri') or '') in seen_ids:
                        continue
                    norm = _normalize_post(post)
                    if norm:
                        items.append(norm)
                        newest = max(newest, norm['observed_at'])

        elif q.bluesky_mode == 'profiles':
            handles = [h.lstrip('@') for h in (q.bluesky_handles or []) if h.strip()][:3]
            if handles:
                profiles = []
                for h in handles:
                    try:
                        profiles.append(await gw.request('/xrpc/app.bsky.actor.getProfile', params={'actor': h}, ttl=600, bucket='core', capacity=120))
                    except ProviderFailure:
                        pass
            else:
                res = await gw.request('/xrpc/app.bsky.actor.searchActors', params={'q': kw, 'limit': 10}, ttl=600, bucket='core', capacity=120)
                profiles = res.get('actors') or []
            for p in profiles[:10]:
                handle = p.get('handle') or ''
                did = p.get('did') or handle
                if not handle or f'profile:{did}' in seen_ids:
                    continue
                norm = connectors.normalized(
                    'Bluesky', f'profile:{did}', f'https://bsky.app/profile/{handle}',
                    p.get('displayName') or handle, p.get('description') or handle,
                    p.get('createdAt') or p.get('indexedAt') or now(),
                    fetch_method='official_api', content_kind='post', author_handle=handle,
                    attribution={'author': providers.text(p.get('displayName') or handle, 100), 'profile_url': f'https://bsky.app/profile/{handle}', 'license': 'Bluesky Public API', 'source': 'Bluesky'},
                )
                if norm:
                    items.append(norm)

        new_seen = list(dict.fromkeys([*(x['source_record_id'] for x in items), *seen_ids]))[:600]
        return {
            'items': items[:q.result_limit],
            'requests': gw.client.requests,
            'scanned': len(items),
            'next_offset': None,
            'cursor': {'seen_ids': new_seen, 'since': newest or None, 'api_cursor': next_cursor},
            'coverage': f'Official Bluesky Public API ({preferred}, mode={q.bluesky_mode}, threads={q.bluesky_threads}) with caching ({gw.cache_hits} hit(s)) and pagination cursor.',
        }


def stream_health(c) -> dict:
    s = get_settings()
    row = c.execute('SELECT * FROM intent_stream_checkpoints WHERE stream_id=?', (STREAM_ID,)).fetchone()
    if not row:
        return {
            'stream_id': STREAM_ID,
            'enabled': bool(s.intent_radar_bluesky_enabled and s.intent_radar_bluesky_jetstream_enabled),
            'endpoint': s.bluesky_jetstream_url,
            'state': 'NEVER_RUN',
            'sequence': 0,
            'updated_at': None,
            'detail': {},
        }
    return {
        'stream_id': row['stream_id'],
        'enabled': bool(s.intent_radar_bluesky_enabled and s.intent_radar_bluesky_jetstream_enabled),
        'endpoint': s.bluesky_jetstream_url,
        'state': row['state'],
        'sequence': int(row['sequence']),
        'updated_at': row['updated_at'],
        'detail': json.loads(row['detail_json'] or '{}'),
    }


def _active_bluesky_monitors(c) -> list[dict]:
    rows = c.execute("SELECT id,organization_id,created_by,configuration_json FROM intent_monitors WHERE status='Active'").fetchall()
    result = []
    for r in rows:
        cfg = json.loads(r['configuration_json'])
        if 'bluesky' in (cfg.get('sources') or []):
            result.append({
                'monitor_id': r['id'],
                'organization_id': r['organization_id'],
                'created_by': r['created_by'],
                'configuration': cfg,
                'keywords': [k.casefold() for k in (cfg.get('keywords') or []) if k],
                'excluded': [k.casefold() for k in (cfg.get('excluded') or []) if k],
            })
    return result


def _apply_jetstream_delete(c, *, did: str, rkey: str, seq: int) -> int:
    uri = f'at://{did}/app.bsky.feed.post/{rkey}'
    native_key = f'{did}/{rkey}'
    deleted_matches = c.execute('DELETE FROM intent_stream_matches WHERE native_id IN (?,?)', (uri, native_key)).rowcount
    rows = c.execute("SELECT id,organization_id FROM intent_signals WHERE source='Bluesky' AND source_record_id IN (?,?) AND available=1", (uri, native_key)).fetchall()
    for row in rows:
        c.execute("UPDATE intent_signals SET available=0, title='Source item unavailable', excerpt='', evidence_json='{}', revision=revision+1 WHERE id=? AND organization_id=?", (row['id'], row['organization_id']))
        c.execute('DELETE FROM intent_analyses WHERE organization_id=? AND signal_id=?', (row['organization_id'], row['id']))
        c.execute('DELETE FROM intent_rankings WHERE organization_id=? AND signal_id=?', (row['organization_id'], row['id']))
        c.execute("UPDATE intent_alerts SET description='Source content unavailable' WHERE organization_id=? AND signal_id=?", (row['organization_id'], row['id']))
    return deleted_matches + len(rows)


def _apply_jetstream_post(c, monitors: list[dict], *, did: str, rkey: str, text_body: str, created_at: str, seq: int) -> int:
    from app.intent_radar import models, classification
    uri = f'at://{did}/app.bsky.feed.post/{rkey}'
    url = _post_url(uri, did)
    lower = text_body.casefold()
    title = providers.text(text_body.splitlines()[0] if text_body else did, 140)
    raw = connectors.normalized(
        'Bluesky', uri, url, title, text_body, created_at or now(),
        fetch_method='official_jetstream', content_kind='post', author_handle=did,
        attribution={'author': did[:100], 'profile_url': f'https://bsky.app/profile/{did}', 'license': 'Bluesky Jetstream v2', 'source': 'Bluesky'},
    )
    if not raw:
        return 0
    matched_count = 0
    expires = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    for m in monitors:
        if not m['keywords'] or not any(k in lower for k in m['keywords']):
            continue
        if any(ex in lower for ex in m['excluded']):
            continue
        query = models.Search.model_validate(m['configuration'])
        item = classification.classify(raw, query)
        if not item:
            continue
        item['evidence'].update(provenance=raw.get('provenance', {}), content_fingerprint=raw.get('content_fingerprint'), search_configuration=m['configuration'])
        org = m['organization_id']
        mon_id = m['monitor_id']
        c.execute(
            'INSERT INTO intent_stream_matches(organization_id,monitor_id,native_id,sequence,operation,record_json,expires_at,updated_at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(organization_id,monitor_id,native_id) DO UPDATE SET sequence=excluded.sequence,operation=excluded.operation,record_json=excluded.record_json,updated_at=excluded.updated_at',
            (org, mon_id, uri, seq, 'create', json.dumps({'uri': uri, 'url': url, 'title': title}), expires, now()),
        )
        signal_id = str(uuid.uuid5(uuid.NAMESPACE_URL, org + ':Bluesky:' + uri))
        c.execute(
            'INSERT INTO intent_signals(id,organization_id,source,source_record_id,source_url,title,excerpt,observed_at,retrieved_at,category,score,evidence_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(organization_id,source,source_record_id) DO NOTHING',
            (signal_id, org, item['source'], item['source_record_id'], item['source_url'], item['title'], item['excerpt'], item['observed_at'], item['retrieved_at'], item['category'], item['score'], json.dumps(item['evidence'])),
        )
        linked = c.execute('INSERT INTO intent_monitor_signals(organization_id,monitor_id,signal_id,matched_at) VALUES(?,?,?,?) ON CONFLICT(organization_id,monitor_id,signal_id) DO NOTHING', (org, mon_id, signal_id, now())).rowcount
        if linked:
            alert_id = str(uuid.uuid5(uuid.NAMESPACE_URL, org + ':intent-alert:match:' + mon_id + ':' + signal_id))
            inserted_alert = c.execute(
                'INSERT INTO intent_alerts(id,organization_id,monitor_id,signal_id,event_key,title,description,created_at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(organization_id,event_key) DO NOTHING',
                (alert_id, org, mon_id, signal_id, 'match:' + mon_id + ':' + signal_id, 'Bluesky stream matched monitor', item['title'][:200], now()),
            ).rowcount
            if inserted_alert and m['created_by']:
                c.execute('INSERT INTO workspace_notifications(id,organization_id,user_id,kind,entity_id,created_at) VALUES(?,?,?,?,?,?)', (str(uuid.uuid4()), org, m['created_by'], 'INTENT_RADAR', alert_id, now()))
        matched_count += 1
    return matched_count


async def poll_jetstream(*, max_seconds: float = 8.0, max_events: int = 250, reconnect_attempts: int = 2) -> dict:
    """Bounded, cost-safe Jetstream v2 consumer with durable sequence cursor, reconnect and delete propagation."""
    s = get_settings()
    if not (s.intent_radar_bluesky_enabled and s.intent_radar_bluesky_jetstream_enabled):
        return {'status': 'DISABLED', 'events': 0, 'matches': 0, 'deletions': 0, 'sequence': 0}

    lease_owner = str(uuid.uuid4())
    lease_until = (datetime.now(timezone.utc) + timedelta(seconds=max(30, int(max_seconds) + 20))).isoformat()
    with db_session() as c:
        monitors = _active_bluesky_monitors(c)
        filter_hash = hashlib.sha256(json.dumps(sorted(m['monitor_id'] for m in monitors)).encode()).hexdigest()
        existing = c.execute('SELECT * FROM intent_stream_checkpoints WHERE stream_id=?', (STREAM_ID,)).fetchone()
        if existing and existing['lease_until'] and existing['lease_until'] > now() and existing['state'] == 'RUNNING':
            return {'status': 'BUSY', 'sequence': int(existing['sequence']), 'events': 0, 'matches': 0, 'deletions': 0}
        last_seq = int(existing['sequence']) if existing else 0
        c.execute(
            "INSERT INTO intent_stream_checkpoints(stream_id,sequence,filter_hash,lease_owner,lease_until,state,detail_json,updated_at) VALUES(?,?,?,?,?,'RUNNING',?,?) ON CONFLICT(stream_id) DO UPDATE SET filter_hash=excluded.filter_hash,lease_owner=excluded.lease_owner,lease_until=excluded.lease_until,state='RUNNING',updated_at=excluded.updated_at",
            (STREAM_ID, last_seq, filter_hash, lease_owner, lease_until, json.dumps({'active_monitors': len(monitors)}), now()),
        )

    import websockets
    events = 0
    commits = 0
    matches = 0
    deletions = 0
    reconnects = 0
    subprotocol = None
    deadline = time.monotonic() + max_seconds
    current_seq = last_seq
    error_code = None

    for attempt in range(max(1, reconnect_attempts)):
        remaining = deadline - time.monotonic()
        if remaining <= 0.5 or events >= max_events:
            break
        qparams = [('collections', 'app.bsky.feed.post'), ('kinds', 'commit')]
        if current_seq > 0:
            qparams.append(('cursor', str(current_seq)))
        ws_url = s.bluesky_jetstream_url + '?' + urlencode(qparams)
        try:
            async with asyncio.timeout(remaining):
                async with websockets.connect(ws_url, subprotocols=['xrpc.v1.json'], open_timeout=6, close_timeout=2, max_size=131072, max_queue=32) as ws:
                    subprotocol = ws.subprotocol
                    async for raw_frame in ws:
                        events += 1
                        frame = json.loads(raw_frame)
                        payload = frame.get('payload') or {}
                        seq = payload.get('seq')
                        if isinstance(seq, int) and seq > current_seq:
                            current_seq = seq
                        if str(payload.get('$type') or '').endswith('#commit'):
                            commits += 1
                            op = payload.get('operation')
                            did = payload.get('did') or ''
                            rkey = payload.get('rkey') or ''
                            if op == 'delete' and did and rkey:
                                with db_session() as c:
                                    deletions += _apply_jetstream_delete(c, did=did, rkey=rkey, seq=current_seq)
                            elif op in ('create', 'update') and did and rkey:
                                rec = payload.get('record') or {}
                                text_body = rec.get('text') or ''
                                if text_body and monitors:
                                    with db_session() as c:
                                        matches += _apply_jetstream_post(c, monitors, did=did, rkey=rkey, text_body=text_body, created_at=rec.get('createdAt') or now(), seq=current_seq)
                        if events >= max_events or time.monotonic() >= deadline:
                            break
            break
        except TimeoutError:
            break
        except Exception as exc:
            error_code = type(exc).__name__
            if attempt + 1 < reconnect_attempts and time.monotonic() + 1.5 < deadline:
                reconnects += 1
                await asyncio.sleep(min(1.0 * (attempt + 1), max(0.2, deadline - time.monotonic() - 0.5)))
                continue
            break

    final_state = 'HEALTHY' if (events > 0 or not error_code) else 'DEGRADED'
    detail = {
        'events': events, 'commits': commits, 'matches': matches, 'deletions': deletions,
        'reconnects': reconnects, 'subprotocol': subprotocol, 'active_monitors': len(monitors),
        'last_error': error_code, 'polled_at': now(),
    }
    with db_session() as c:
        c.execute(
            "UPDATE intent_stream_checkpoints SET sequence=?, state=?, lease_owner=NULL, lease_until=NULL, detail_json=?, updated_at=? WHERE stream_id=? AND lease_owner=?",
            (current_seq, final_state, json.dumps(detail), now(), STREAM_ID, lease_owner),
        )
    return {'status': final_state, 'sequence': current_seq, **detail}
