"""Persistent Discovery History (immutable runs) and reusable Saved Searches."""
import json
import uuid
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from app.database.discovery_workspace_schema import ensure_sqlite_tables
from app.database.prospects import now
from app.intent_radar import models
from app.intent_radar.permissions import context
from app.workflows.service import lock


class SavedSearchInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=120)
    description: str = Field('', max_length=1000)
    original_prompt: str = Field('', max_length=2000)
    configuration: models.Search
    revision: int | None = Field(None, ge=1)


def _derive_title(cfg: dict, explicit_title: str = '', original_prompt: str = '') -> str:
    if explicit_title and explicit_title.strip():
        return explicit_title.strip()[:120]
    kws = [k for k in (cfg.get('keywords') or []) if isinstance(k, str) and k.strip()]
    if kws:
        return (' · '.join(kws[:3]))[:120]
    if original_prompt and original_prompt.strip():
        return original_prompt.strip()[:120]
    return 'Untitled discovery'


def _has_meta_table(c) -> bool:
    ensure_sqlite_tables(c)
    try:
        c.execute('SELECT 1 FROM intent_discovery_runs_meta LIMIT 1')
        return True
    except Exception:
        return False


def _has_saved_table(c) -> bool:
    ensure_sqlite_tables(c)
    try:
        c.execute('SELECT 1 FROM intent_saved_searches LIMIT 1')
        return True
    except Exception:
        return False


def record_run_metadata(
    c,
    *,
    organization_id: str,
    discovery_id: str,
    configuration: dict,
    title: str = '',
    original_prompt: str = '',
    search_mode: str = 'advanced',
    parent_discovery_id: str | None = None,
    strategy: dict | None = None,
):
    if not _has_meta_table(c):
        return
    clean_mode = search_mode if search_mode in ('ai', 'advanced', 'monitor', 'rerun') else 'advanced'
    final_title = _derive_title(configuration, title, original_prompt)
    c.execute(
        """INSERT INTO intent_discovery_runs_meta(
             organization_id, discovery_id, title, original_prompt, search_mode,
             parent_discovery_id, strategy_json, deleted_at, updated_at
           ) VALUES(?,?,?,?,?,?,?,NULL,?)
           ON CONFLICT(organization_id, discovery_id) DO NOTHING""",
        (
            organization_id,
            discovery_id,
            final_title,
            (original_prompt or '')[:2000],
            clean_mode,
            parent_discovery_id,
            json.dumps(strategy or {}, sort_keys=True),
            now(),
        ),
    )


def _assemble_run_row(c, org: str, row: dict, *, include_signals: bool = False) -> dict:
    cfg = json.loads(row['configuration_json'] or '{}')
    discovery_id = row['id']

    job_row = c.execute(
        """SELECT j.id AS job_id, j.status AS job_status, j.error_code, j.attempts,
                  j.created_at AS job_created_at, j.updated_at AS job_updated_at,
                  i.status AS item_status, i.result_json AS item_result_json, i.error_code AS item_error_code
           FROM intelligence_job_items i
           JOIN intelligence_jobs j ON j.id = i.job_id
           WHERE j.organization_id = ? AND i.resource_id = ? AND j.kind = 'INTENT_DISCOVER'
           ORDER BY j.created_at DESC LIMIT 1""",
        (org, discovery_id),
    ).fetchone()

    source_runs = [
        {
            'provider': sr['provider'],
            'status': sr['status'],
            **(json.loads(sr['result_json'] or '{}')),
        }
        for sr in c.execute(
            'SELECT provider, status, result_json FROM intent_source_runs WHERE organization_id=? AND discovery_id=? ORDER BY provider',
            (org, discovery_id),
        ).fetchall()
    ]

    item_result = json.loads(job_row['item_result_json'] or '{}') if job_row and job_row['item_result_json'] else {}
    signal_ids = list(dict.fromkeys(
        list(item_result.get('signals') or [])
        + [sid for sr in source_runs for sid in (sr.get('signals') or [])]
    ))

    matched_count = item_result.get('matched')
    if matched_count is None:
        matched_count = len(signal_ids)
    scanned_count = item_result.get('scanned')
    if scanned_count is None:
        scanned_count = sum(int(sr.get('scanned') or 0) for sr in source_runs)
    requests_count = item_result.get('requests')
    if requests_count is None:
        requests_count = sum(int(sr.get('requests') or 0) for sr in source_runs)

    raw_status = (job_row['job_status'] if job_row else None) or 'QUEUED'
    if raw_status in ('COMPLETED', 'COMPLETE') and any(sr.get('status') not in ('COMPLETE', 'NO_RESULTS') for sr in source_runs):
        effective_status = 'PARTIAL'
    else:
        effective_status = raw_status

    strategy = {}
    if row.get('strategy_json'):
        try:
            strategy = json.loads(row['strategy_json'] or '{}')
        except ValueError:
            strategy = {}

    sources = cfg.get('sources') or ['hacker_news']
    title = _derive_title(cfg, row.get('meta_title') or '', row.get('original_prompt') or '')
    record = {
        'id': discovery_id,
        'job_id': job_row['job_id'] if job_row else None,
        'title': title,
        'original_prompt': row.get('original_prompt') or '',
        'search_mode': row.get('search_mode') or ('monitor' if row.get('monitor_id') else 'advanced'),
        'parent_discovery_id': row.get('parent_discovery_id'),
        'monitor_id': row.get('monitor_id'),
        'created_by': row['created_by'],
        'created_at': row['created_at'],
        'completed_at': job_row['job_updated_at'] if job_row and effective_status not in ('QUEUED', 'RUNNING') else None,
        'status': effective_status,
        'error_code': (job_row['error_code'] or job_row['item_error_code']) if job_row else None,
        'attempts': job_row['attempts'] if job_row else 0,
        'sources': sources,
        'keywords': cfg.get('keywords') or [],
        'matched_count': matched_count,
        'scanned_count': scanned_count,
        'requests_count': requests_count,
        'coverage': item_result.get('coverage') or '; '.join(sr.get('coverage', '') for sr in source_runs if sr.get('coverage')),
        'configuration': cfg,
        'strategy': strategy or None,
        'source_runs': [
            {
                'provider': sr['provider'],
                'status': sr['status'],
                'scanned': sr.get('scanned') or 0,
                'requests': sr.get('requests'),
                'coverage': sr.get('coverage') or '',
                'signals_count': len(sr.get('signals') or []),
                'retry_at': sr.get('retry_at'),
            }
            for sr in source_runs
        ],
        'signal_ids': signal_ids[:50],
    }

    if include_signals:
        signals = []
        if signal_ids:
            placeholders = ','.join('?' for _ in signal_ids[:50])
            saved_set = {
                r['signal_id']
                for r in c.execute(
                    f'SELECT signal_id FROM intent_saved_signals WHERE organization_id=? AND signal_id IN ({placeholders})',
                    (org, *signal_ids[:50]),
                ).fetchall()
            }
            rows = c.execute(
                f'SELECT * FROM intent_signals WHERE organization_id=? AND available=1 AND id IN ({placeholders})',
                (org, *signal_ids[:50]),
            ).fetchall()
            by_id = {r['id']: r for r in rows}
            for sid in signal_ids[:50]:
                r = by_id.get(sid)
                if not r:
                    continue
                signals.append({
                    'id': r['id'],
                    'title': r['title'],
                    'source': r['source'],
                    'source_url': r['source_url'],
                    'excerpt': r['excerpt'],
                    'observed_at': r['observed_at'],
                    'retrieved_at': r['retrieved_at'],
                    'category': r['category'],
                    'score': r['score'],
                    'status': r['status'],
                    'notes': r['notes'],
                    'revision': r['revision'],
                    'available': r['available'],
                    'saved': r['id'] in saved_set,
                    'evidence': json.loads(r['evidence_json'] or '{}'),
                    'monitors': [],
                })
        record['signals'] = signals
    return record


def list_discoveries(
    c,
    *,
    page: int = 1,
    page_size: int = 20,
    search: str = '',
    source: str = '',
    status: str = '',
    from_date: str = '',
    to_date: str = '',
    created_by: str = '',
) -> dict:
    ctx = context(c)
    org = ctx.organization_id
    has_meta = _has_meta_table(c)
    if has_meta:
        rows = c.execute(
            """SELECT d.id, d.organization_id, d.created_by, d.monitor_id, d.configuration_json, d.created_at,
                      m.title AS meta_title, m.original_prompt, m.search_mode, m.parent_discovery_id,
                      m.strategy_json, m.deleted_at
               FROM intent_discoveries d
               LEFT JOIN intent_discovery_runs_meta m
                 ON m.organization_id = d.organization_id AND m.discovery_id = d.id
               WHERE d.organization_id = ? AND (m.deleted_at IS NULL)
               ORDER BY d.created_at DESC LIMIT 200""",
            (org,),
        ).fetchall()
    else:
        rows = c.execute(
            """SELECT id, organization_id, created_by, monitor_id, configuration_json, created_at
               FROM intent_discoveries WHERE organization_id = ?
               ORDER BY created_at DESC LIMIT 200""",
            (org,),
        ).fetchall()

    q = (search or '').strip().casefold()
    src = (source or '').strip().casefold()
    st = (status or '').strip().upper()
    actor_filter = (created_by or '').strip().casefold()

    assembled = []
    for raw in rows:
        item = _assemble_run_row(c, org, dict(raw), include_signals=False)
        if q:
            hay = ' '.join([
                item['title'],
                item['original_prompt'],
                ' '.join(item['keywords']),
                ' '.join(item['sources']),
            ]).casefold()
            if q not in hay:
                continue
        if src and src not in [s.casefold() for s in item['sources']]:
            continue
        if st:
            if st == 'NO_RESULTS':
                if not (item['status'] in ('COMPLETE', 'COMPLETED') and item['matched_count'] == 0):
                    continue
            elif st in ('COMPLETE', 'COMPLETED'):
                if item['status'] not in ('COMPLETE', 'COMPLETED'):
                    continue
            elif item['status'] != st:
                continue
        if from_date and item['created_at'][:10] < from_date:
            continue
        if to_date and item['created_at'][:10] > to_date:
            continue
        if actor_filter and item['created_by'].casefold() != actor_filter:
            continue
        assembled.append(item)

    total = len(assembled)
    start = (page - 1) * page_size
    return {
        'items': assembled[start : start + page_size],
        'total': total,
        'page': page,
        'page_size': page_size,
    }


def get_discovery(c, discovery_id: str) -> dict:
    ctx = context(c)
    org = ctx.organization_id
    has_meta = _has_meta_table(c)
    if has_meta:
        row = c.execute(
            """SELECT d.id, d.organization_id, d.created_by, d.monitor_id, d.configuration_json, d.created_at,
                      m.title AS meta_title, m.original_prompt, m.search_mode, m.parent_discovery_id,
                      m.strategy_json, m.deleted_at
               FROM intent_discoveries d
               LEFT JOIN intent_discovery_runs_meta m
                 ON m.organization_id = d.organization_id AND m.discovery_id = d.id
               WHERE d.organization_id = ? AND d.id = ?""",
            (org, discovery_id),
        ).fetchone()
    else:
        row = c.execute(
            'SELECT id, organization_id, created_by, monitor_id, configuration_json, created_at FROM intent_discoveries WHERE organization_id=? AND id=?',
            (org, discovery_id),
        ).fetchone()
    if not row or (has_meta and row['deleted_at']):
        raise HTTPException(404, 'Discovery run not found.')
    return _assemble_run_row(c, org, dict(row), include_signals=True)


def delete_discovery(c, discovery_id: str) -> dict:
    ctx = context(c, True)
    org = ctx.organization_id
    row = c.execute(
        'SELECT id, configuration_json FROM intent_discoveries WHERE organization_id=? AND id=?',
        (org, discovery_id),
    ).fetchone()
    if not row:
        raise HTTPException(404, 'Discovery run not found.')
    if not _has_meta_table(c):
        raise HTTPException(503, 'Discovery history deletion requires schema migration 1008.')
    lock(c)
    cfg = json.loads(row['configuration_json'] or '{}')
    stamp = now()
    c.execute(
        """INSERT INTO intent_discovery_runs_meta(
             organization_id, discovery_id, title, original_prompt, search_mode,
             parent_discovery_id, strategy_json, deleted_at, updated_at
           ) VALUES(?,?,?,'','advanced',NULL,'{}',?,?)
           ON CONFLICT(organization_id, discovery_id) DO UPDATE SET deleted_at=excluded.deleted_at, updated_at=excluded.updated_at""",
        (org, discovery_id, _derive_title(cfg), stamp, stamp),
    )
    from app.intent_radar.service import audit
    audit(c, 'DISCOVERY_HISTORY_DELETED', discovery_id)
    return {'deleted': True, 'id': discovery_id}


def list_saved_searches(c, *, search: str = '', page: int = 1, page_size: int = 50) -> dict:
    ctx = context(c)
    org = ctx.organization_id
    if not _has_saved_table(c):
        return {'items': [], 'total': 0, 'page': page, 'page_size': page_size}
    rows = c.execute(
        'SELECT * FROM intent_saved_searches WHERE organization_id=? ORDER BY updated_at DESC LIMIT 200',
        (org,),
    ).fetchall()
    q = (search or '').strip().casefold()
    items = []
    for r in rows:
        cfg = json.loads(r['configuration_json'] or '{}')
        entry = {
            'id': r['id'],
            'name': r['name'],
            'description': r['description'],
            'original_prompt': r['original_prompt'],
            'configuration': cfg,
            'revision': r['revision'],
            'last_run_discovery_id': r['last_run_discovery_id'],
            'created_by': r['created_by'],
            'created_at': r['created_at'],
            'updated_at': r['updated_at'],
        }
        if q:
            hay = f"{entry['name']} {entry['description']} {' '.join(cfg.get('keywords') or [])}".casefold()
            if q not in hay:
                continue
        items.append(entry)
    total = len(items)
    start = (page - 1) * page_size
    return {'items': items[start : start + page_size], 'total': total, 'page': page, 'page_size': page_size}


def save_search(c, body: SavedSearchInput, key: str | None = None) -> dict:
    ctx = context(c, True)
    org = ctx.organization_id
    if not _has_saved_table(c):
        raise HTTPException(503, 'Saved searches require schema migration 1008.')
    from app.intent_radar import connectors
    connectors.validate(c, body.configuration)
    lock(c)
    encoded = body.configuration.model_dump_json()
    stamp = now()
    if key:
        old = c.execute(
            'SELECT * FROM intent_saved_searches WHERE organization_id=? AND id=?',
            (org, key),
        ).fetchone()
        if not old:
            raise HTTPException(404, 'Saved search not found.')
        if body.revision is not None and old['revision'] != body.revision:
            raise HTTPException(409, 'Saved search changed; reload before editing.')
        c.execute(
            """UPDATE intent_saved_searches
               SET name=?, description=?, original_prompt=?, configuration_json=?, revision=revision+1, updated_at=?
               WHERE organization_id=? AND id=?""",
            (body.name, body.description, body.original_prompt, encoded, stamp, org, key),
        )
    else:
        count = c.execute('SELECT COUNT(*) FROM intent_saved_searches WHERE organization_id=?', (org,)).fetchone()[0]
        if count >= 100:
            raise HTTPException(429, 'Saved search limit reached (100). Remove an unused saved search first.')
        key = str(uuid.uuid4())
        c.execute(
            """INSERT INTO intent_saved_searches(
                 id, organization_id, created_by, name, description, original_prompt,
                 configuration_json, revision, created_at, updated_at
               ) VALUES(?,?,?,?,?,?,?,1,?,?)""",
            (key, org, ctx.actor, body.name, body.description, body.original_prompt, encoded, stamp, stamp),
        )
    from app.intent_radar.service import audit
    audit(c, 'SAVED_SEARCH_WRITTEN', key)
    row = c.execute('SELECT * FROM intent_saved_searches WHERE organization_id=? AND id=?', (org, key)).fetchone()
    return {
        'id': row['id'],
        'name': row['name'],
        'description': row['description'],
        'original_prompt': row['original_prompt'],
        'configuration': json.loads(row['configuration_json']),
        'revision': row['revision'],
        'last_run_discovery_id': row['last_run_discovery_id'],
        'created_by': row['created_by'],
        'created_at': row['created_at'],
        'updated_at': row['updated_at'],
    }


def duplicate_saved_search(c, key: str) -> dict:
    ctx = context(c, True)
    org = ctx.organization_id
    if not _has_saved_table(c):
        raise HTTPException(503, 'Saved searches require schema migration 1008.')
    old = c.execute('SELECT * FROM intent_saved_searches WHERE organization_id=? AND id=?', (org, key)).fetchone()
    if not old:
        raise HTTPException(404, 'Saved search not found.')
    body = SavedSearchInput(
        name=(old['name'] + ' (copy)')[:120],
        description=old['description'],
        original_prompt=old['original_prompt'],
        configuration=models.Search.model_validate(json.loads(old['configuration_json'])),
    )
    return save_search(c, body)


def delete_saved_search(c, key: str) -> dict:
    ctx = context(c, True)
    org = ctx.organization_id
    if not _has_saved_table(c):
        raise HTTPException(503, 'Saved searches require schema migration 1008.')
    lock(c)
    deleted = c.execute(
        'DELETE FROM intent_saved_searches WHERE organization_id=? AND id=?',
        (org, key),
    ).rowcount
    if not deleted:
        raise HTTPException(404, 'Saved search not found.')
    from app.intent_radar.service import audit
    audit(c, 'SAVED_SEARCH_DELETED', key)
    return {'deleted': True, 'id': key}
