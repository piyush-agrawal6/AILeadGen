"""Persistent Discovery History (immutable runs, scalable queries) and reusable Saved Searches."""
import json
import re
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


class DiscoveryRenameInput(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    title: str = Field(min_length=1, max_length=120)


_GENERIC_TITLES = {'reviewable intent search', 'untitled discovery', 'intent search', 'discovery'}
_LEADING_VERBS_RE = re.compile(
    r'^(?:please\s+)?(?:find|search(?:\s+for)?|look(?:ing)?\s+for|show(?:\s+me)?|discover|get|list|track|monitor)\s+'
    r'(?:all\s+|any\s+|recent\s+|latest\s+|public\s+|online\s+)*'
    r'(?:discussions?|conversations?|posts?|threads?|mentions?|people|teams|founders|companies|developers|startups)?\s*'
    r'(?:(?:especially|only)\s+)?(?:(?:on|in|from)\s+(?:github|hacker\s*news|stack\s*(?:overflow|exchange)|youtube|bluesky|discourse|rss|atom)(?:\s+and\s+(?:github|hacker\s*news|stack\s*(?:overflow|exchange)|youtube|bluesky|discourse|rss|atom))?\s+)?'
    r'(?:about|regarding|for|discussing|comparing|asking\s+(?:for|about)|looking\s+for|dealing\s+with|struggling\s+with|hitting|switching\s+from)?\s*',
    re.I,
)


def _format_keyword_phrase(kw: str) -> str:
    """Format a single keyword/phrase into readable title casing while preserving acronyms/brand punctuation."""
    s = kw.strip()
    if not s:
        return ''
    if any(ch.isupper() for ch in s[1:]) or '.' in s or '/' in s:
        # Preserve intentional casing like Next.js, HubSpot, CI/CD, SOC2, GraphQL
        return s[0].upper() + s[1:]
    words = s.split()
    out = []
    for w in words:
        lw = w.lower()
        if lw in {'ai', 'ml', 'crm', 'erp', 'api', 'sdk', 'seo', 'b2b', 'saas', 'soc', 'mvp', 'llm', 'rag', 'sql', 'aws', 'gcp', 'ci/cd', 'sso', 'iam'}:
            out.append(lw.upper() if lw != 'saas' else 'SaaS')
        elif lw in {'vs', 'or', 'and', 'for', 'of', 'to', 'in', 'on'}:
            out.append(lw)
        else:
            out.append(w.capitalize())
    return ' '.join(out)


def _derive_title(cfg: dict, explicit_title: str = '', original_prompt: str = '') -> str:
    from app.intent_radar.discovery_copilot import clean_keywords

    if explicit_title and explicit_title.strip() and explicit_title.strip().casefold() not in _GENERIC_TITLES:
        raw_t = explicit_title.strip()
        # If an older auto-derived title was just filler words joined by middots, improve it cleanly
        parts = [p.strip() for p in raw_t.split('·') if p.strip()]
        if len(parts) >= 2:
            cleaned_parts = clean_keywords(parts, max_items=3)
            if not cleaned_parts or len(cleaned_parts) < len(parts):
                explicit_title = ''
            else:
                return raw_t[:120]
        else:
            return raw_t[:120]

    # 1. Derive concise objective title from user-provided prompt when available
    if original_prompt and original_prompt.strip():
        stripped = _LEADING_VERBS_RE.sub('', original_prompt.strip()).strip(' .,:;!?-"\'')
        stripped = re.sub(r'\s+', ' ', stripped)
        if len(stripped) >= 8:
            nice = stripped[0].upper() + stripped[1:]
            if len(nice) > 72:
                nice = nice[:69].rsplit(' ', 1)[0].rstrip(' ,;:') + '…'
            return nice[:120]

    # 2. Derive clean, filler-free title from keywords
    raw_kws = [k for k in (cfg.get('keywords') or []) if isinstance(k, str) and k.strip()]
    good_kws = clean_keywords(raw_kws, max_items=3) or raw_kws[:3]
    if good_kws:
        formatted = [_format_keyword_phrase(k) for k in good_kws[:2]]
        if len(formatted) == 1:
            base = formatted[0]
            return (f'{base} Research' if len(base.split()) <= 2 and 'research' not in base.lower() else base)[:120]
        return f"{formatted[0]} & {formatted[1]} Research"[:120]

    return 'Discovery Research'


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


def _build_run_record(row: dict, job_row: dict | None, source_runs: list[dict]) -> dict:
    cfg = json.loads(row['configuration_json'] or '{}')
    discovery_id = row['id']

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
    if raw_status in ('COMPLETED', 'COMPLETE'):
        if any(sr.get('status') not in ('COMPLETE', 'NO_RESULTS') for sr in source_runs):
            effective_status = 'PARTIAL'
        elif matched_count == 0 and source_runs:
            effective_status = 'NO_RESULTS'
        else:
            effective_status = 'COMPLETED'
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
    return {
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


def _batch_hydrate_runs(c, org: str, rows: list[dict]) -> list[dict]:
    """Hydrate discovery runs using 2 bounded IN(...) queries instead of N+1 queries."""
    if not rows:
        return []
    ids = [r['id'] for r in rows]
    jobs_by_disc: dict[str, dict] = {}
    sources_by_disc: dict[str, list[dict]] = {d_id: [] for d_id in ids}

    # Chunk in batches of 200 to stay comfortably below SQL parameter limits on large datasets
    for idx in range(0, len(ids), 200):
        chunk = ids[idx : idx + 200]
        ph = ','.join('?' for _ in chunk)
        job_rows = c.execute(
            f"""SELECT i.resource_id, j.id AS job_id, j.status AS job_status, j.error_code, j.attempts,
                       j.created_at AS job_created_at, j.updated_at AS job_updated_at,
                       i.status AS item_status, i.result_json AS item_result_json, i.error_code AS item_error_code
                FROM intelligence_job_items i
                JOIN intelligence_jobs j ON j.id = i.job_id
                WHERE j.organization_id = ? AND j.kind = 'INTENT_DISCOVER' AND i.resource_id IN ({ph})
                ORDER BY j.created_at DESC""",
            (org, *chunk),
        ).fetchall()
        for jr in job_rows:
            rid = jr['resource_id']
            if rid not in jobs_by_disc:
                jobs_by_disc[rid] = dict(jr)

        sr_rows = c.execute(
            f"""SELECT discovery_id, provider, status, result_json
                FROM intent_source_runs
                WHERE organization_id = ? AND discovery_id IN ({ph})
                ORDER BY provider""",
            (org, *chunk),
        ).fetchall()
        for sr in sr_rows:
            sources_by_disc.setdefault(sr['discovery_id'], []).append({
                'provider': sr['provider'],
                'status': sr['status'],
                **(json.loads(sr['result_json'] or '{}')),
            })

    return [_build_run_record(r, jobs_by_disc.get(r['id']), sources_by_disc.get(r['id'], [])) for r in rows]


def _attach_signals(c, org: str, record: dict) -> dict:
    signal_ids = record.get('signal_ids') or []
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
    search_mode: str = '',
    has_results: str = '',
    from_date: str = '',
    to_date: str = '',
    created_by: str = '',
    sort: str = 'newest',
) -> dict:
    ctx = context(c)
    org = ctx.organization_id
    has_meta = _has_meta_table(c)

    where = ['d.organization_id = ?']
    params: list = [org]
    if has_meta:
        where.append('(m.deleted_at IS NULL)')
    if from_date:
        where.append('d.created_at >= ?')
        params.append(from_date)
    if to_date:
        where.append('d.created_at <= ?')
        params.append(to_date + 'T23:59:59.999999+99:99')
    if created_by and created_by.strip():
        where.append('LOWER(d.created_by) = ?')
        params.append(created_by.strip().casefold())
    if has_meta and search_mode and search_mode.strip():
        sm = search_mode.strip().casefold()
        if sm == 'monitor':
            where.append("(m.search_mode = 'monitor' OR d.monitor_id IS NOT NULL)")
        elif sm == 'advanced':
            where.append("(m.search_mode = 'advanced' OR (m.search_mode IS NULL AND d.monitor_id IS NULL))")
        else:
            where.append('m.search_mode = ?')
            params.append(sm)

    q = (search or '').strip().casefold()
    src = (source or '').strip().casefold()
    st = (status or '').strip().upper()
    hr = (has_results or '').strip().casefold()

    if q:
        like = f'%{q}%'
        if has_meta:
            where.append('(LOWER(COALESCE(m.title, \'\')) LIKE ? OR LOWER(COALESCE(m.original_prompt, \'\')) LIKE ? OR LOWER(d.configuration_json) LIKE ?)')
            params.extend([like, like, like])
        else:
            where.append('LOWER(d.configuration_json) LIKE ?')
            params.append(like)

    if src:
        where.append('LOWER(d.configuration_json) LIKE ?')
        params.append(f'%"{src}"%')

    where_sql = ' AND '.join(where)
    base_order = 'd.created_at ASC, d.id ASC' if sort == 'oldest' else 'd.created_at DESC, d.id DESC'

    # Fast SQL-level pagination path when no post-hydration filter/sort is active
    can_sql_paginate = (not st) and (not hr) and sort in ('newest', 'oldest')

    if has_meta:
        from_sql = (
            'FROM intent_discoveries d '
            'LEFT JOIN intent_discovery_runs_meta m '
            'ON m.organization_id = d.organization_id AND m.discovery_id = d.id '
            f'WHERE {where_sql}'
        )
        select_cols = (
            'd.id, d.organization_id, d.created_by, d.monitor_id, d.configuration_json, d.created_at, '
            'm.title AS meta_title, m.original_prompt, m.search_mode, m.parent_discovery_id, '
            'm.strategy_json, m.deleted_at'
        )
    else:
        from_sql = f'FROM intent_discoveries d WHERE {where_sql}'
        select_cols = 'd.id, d.organization_id, d.created_by, d.monitor_id, d.configuration_json, d.created_at'

    if can_sql_paginate:
        total = c.execute(f'SELECT COUNT(*) {from_sql}', tuple(params)).fetchone()[0]
        offset = (page - 1) * page_size
        page_rows = [
            dict(r)
            for r in c.execute(
                f'SELECT {select_cols} {from_sql} ORDER BY {base_order} LIMIT ? OFFSET ?',
                (*params, page_size, offset),
            ).fetchall()
        ]
        items = _batch_hydrate_runs(c, org, page_rows)
        return {
            'items': items,
            'total': total,
            'page': page,
            'page_size': page_size,
            'sort': sort,
            'has_more': offset + len(items) < total,
        }

    # Filtered/hydrated-sort path (bounded to 2000 matching rows per workspace, batch-hydrated)
    raw_rows = [
        dict(r)
        for r in c.execute(
            f'SELECT {select_cols} {from_sql} ORDER BY {base_order} LIMIT 2000',
            tuple(params),
        ).fetchall()
    ]
    hydrated = _batch_hydrate_runs(c, org, raw_rows)

    filtered = []
    for item in hydrated:
        if src and src not in [s.casefold() for s in item['sources']]:
            continue
        if st:
            if st == 'NO_RESULTS':
                if item['status'] != 'NO_RESULTS' and not (item['status'] in ('COMPLETE', 'COMPLETED') and item['matched_count'] == 0):
                    continue
            elif st in ('COMPLETE', 'COMPLETED'):
                if item['status'] not in ('COMPLETE', 'COMPLETED', 'NO_RESULTS'):
                    continue
            elif item['status'] != st:
                continue
        if hr == 'with_results' and item['matched_count'] <= 0:
            continue
        if hr == 'no_results' and item['matched_count'] != 0:
            continue
        filtered.append(item)

    if sort == 'oldest':
        filtered.sort(key=lambda x: (x['created_at'], x['id']))
    elif sort == 'title_asc':
        filtered.sort(key=lambda x: (x['title'].casefold(), x['id']))
    elif sort == 'title_desc':
        filtered.sort(key=lambda x: (x['title'].casefold(), x['id']), reverse=True)
    elif sort == 'results_desc':
        filtered.sort(key=lambda x: (-x['matched_count'], x['created_at']), reverse=False)
        filtered.sort(key=lambda x: (x['matched_count'], x['created_at'], x['id']), reverse=True)
    elif sort == 'results_asc':
        filtered.sort(key=lambda x: (x['matched_count'], x['created_at'], x['id']))
    else:
        filtered.sort(key=lambda x: (x['created_at'], x['id']), reverse=True)

    total = len(filtered)
    start = (page - 1) * page_size
    page_items = filtered[start : start + page_size]
    return {
        'items': page_items,
        'total': total,
        'page': page,
        'page_size': page_size,
        'sort': sort,
        'has_more': start + len(page_items) < total,
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
    hydrated = _batch_hydrate_runs(c, org, [dict(row)])[0]
    return _attach_signals(c, org, hydrated)


def rename_discovery(c, discovery_id: str, title: str) -> dict:
    """Rename a discovery run's display title without modifying immutable original criteria."""
    ctx = context(c, True)
    org = ctx.organization_id
    row = c.execute(
        'SELECT id, monitor_id, configuration_json FROM intent_discoveries WHERE organization_id=? AND id=?',
        (org, discovery_id),
    ).fetchone()
    if not row:
        raise HTTPException(404, 'Discovery run not found.')
    if not _has_meta_table(c):
        raise HTTPException(503, 'Renaming discovery runs requires schema migration 1008.')
    existing = c.execute(
        'SELECT deleted_at FROM intent_discovery_runs_meta WHERE organization_id=? AND discovery_id=?',
        (org, discovery_id),
    ).fetchone()
    if existing and existing['deleted_at']:
        raise HTTPException(404, 'Discovery run not found.')
    clean_title = title.strip()[:120]
    if not clean_title:
        raise HTTPException(422, 'Discovery title cannot be empty.')
    lock(c)
    stamp = now()
    default_mode = 'monitor' if row['monitor_id'] else 'advanced'
    c.execute(
        """INSERT INTO intent_discovery_runs_meta(
             organization_id, discovery_id, title, original_prompt, search_mode,
             parent_discovery_id, strategy_json, deleted_at, updated_at
           ) VALUES(?,?,?,'',?,NULL,'{}',NULL,?)
           ON CONFLICT(organization_id, discovery_id) DO UPDATE SET title=excluded.title, updated_at=excluded.updated_at""",
        (org, discovery_id, clean_title, default_mode, stamp),
    )
    from app.intent_radar.service import audit
    audit(c, 'DISCOVERY_HISTORY_RENAMED', discovery_id)
    return {'id': discovery_id, 'title': clean_title}


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
