"""YouTube Data API v3 source adapter with fair-usage quotas, caching, 30-day retention and AI policy gates."""
from app.config.settings import get_settings
from app.intent_radar import connectors, providers
from app.intent_radar.permissions import context
from app.intent_radar.source_http import ProviderFailure
from app.intent_radar.source_runtime import Gateway, reserve


def policy_state() -> dict:
    s = get_settings()
    key_ok = bool(s.youtube_api_key.get_secret_value())
    return {
        'enabled': bool(s.intent_radar_youtube_enabled and key_ok),
        'search_enabled': bool(s.intent_radar_youtube_enabled and s.intent_radar_youtube_search_enabled and key_ok),
        'comments_enabled': bool(s.intent_radar_youtube_enabled and s.intent_radar_youtube_comments_enabled and key_ok),
        'monitoring_enabled': bool(s.intent_radar_youtube_enabled and s.intent_radar_youtube_monitoring_enabled and key_ok),
        'ai_analytics_enabled': bool(s.intent_radar_youtube_ai_analytics_enabled),
        'cross_source_analytics_enabled': bool(s.intent_radar_youtube_cross_source_analytics_enabled),
        'retention_days': 30,
        'policy_note': (
            'YouTube Data API v3 retrieval (videos, channels, public comments) is active. '
            + ('Derived AI analytics are explicitly authorized.' if s.intent_radar_youtube_ai_analytics_enabled else 'Derived AI sentiment/intent scoring and cross-platform AI analytics remain gated pending separate YouTube API policy approval.')
        ),
    }


class YouTubeCollector:
    async def fetch(self, c, q, permit):
        org = context(c).organization_id
        s = get_settings()
        api_key = s.youtube_api_key.get_secret_value()
        if not (s.intent_radar_youtube_enabled and s.intent_radar_youtube_search_enabled and api_key):
            raise connectors.SourceUnavailable('YOUTUBE_NOT_CONFIGURED')

        # Public YouTube Data API v3 responses are cacheable across workspaces (public=True)
        # while per-workspace fair-usage budgets prevent one customer from starving others.
        gw = Gateway(c, 'youtube', 'https://www.googleapis.com/youtube/v3', permit, public=True, seconds=26, max_requests=14)
        kw = ' '.join(q.keywords[:4])
        seen_ids = set(q._collection_cursor.get('seen_ids') or [])
        since = q._collection_cursor.get('published_after')
        if q.from_date:
            from_iso = q.from_date.isoformat() + 'T00:00:00Z'
            since = max(since, from_iso) if since else from_iso
        until = (q.to_date.isoformat() + 'T23:59:59Z') if q.to_date else None

        ai_ok = bool(s.intent_radar_youtube_ai_analytics_enabled)
        policy_note = None if ai_ok else 'YouTube derived AI analytics gated pending API policy approval; source display and bookmarking remain available.'
        items = []
        newest = since or ''
        video_ids: list[str] = []
        channel_ids: list[str] = [ch.strip() for ch in (q.youtube_channel_ids or []) if ch.strip()][:3]
        comments_disabled_count = 0

        # 1. Search videos (or channels) — reserve workspace fair-usage search budget BEFORE uncached search
        async def run_search(search_type: str, channel_id: str | None = None, max_results: int = 5):
            params = {
                'part': 'snippet',
                'q': kw,
                'type': search_type,
                'maxResults': max(1, min(8, max_results)),
                'order': 'date' if since else 'relevance',
                'safeSearch': 'strict',
                'key': api_key,
            }
            if channel_id:
                params['channelId'] = channel_id
            if since:
                params['publishedAfter'] = since
            if until:
                params['publishedBefore'] = until
            # Reserve workspace daily fair-usage search allowance (checked only if not in shared cache)
            fp = gw.fingerprint('/search', params, None)
            cached = c.execute("SELECT 1 FROM intent_provider_cache WHERE provider='youtube' AND scope='public' AND fingerprint=? AND state='READY' AND expires_at>?", (fp, connectors.now())).fetchone()
            if not cached:
                reserve('youtube', 'search', s.youtube_workspace_daily_search_limit, scope='workspace:' + org, cost=1)
            return await gw.request('/search', params=params, ttl=900, bucket='search', capacity=s.youtube_daily_search_limit, cost=1)

        if q.youtube_mode in ('videos', 'both'):
            targets = channel_ids if channel_ids else [None]
            for ch_id in targets[:2]:
                res = await run_search('video', channel_id=ch_id, max_results=5 if not ch_id else 3)
                for entry in res.get('items') or []:
                    vid = (entry.get('id') or {}).get('videoId')
                    if vid and vid not in video_ids:
                        video_ids.append(vid)

        if q.youtube_mode in ('channels', 'both') and not channel_ids:
            res = await run_search('channel', max_results=3)
            for entry in res.get('items') or []:
                cid = (entry.get('id') or {}).get('channelId')
                if cid and cid not in channel_ids:
                    channel_ids.append(cid)

        # 2. Fetch video metadata & statistics in a single batched call (1 unit!)
        video_meta = {}
        if video_ids:
            reserve('youtube', 'core', s.youtube_workspace_daily_unit_limit, scope='workspace:' + org, cost=1)
            vdata = await gw.request(
                '/videos',
                params={'part': 'snippet,contentDetails,statistics', 'id': ','.join(video_ids[:8]), 'key': api_key},
                ttl=600, bucket='core', capacity=s.youtube_daily_unit_limit, cost=1,
            )
            for v in vdata.get('items') or []:
                vid = v.get('id')
                snip = v.get('snippet') or {}
                stats = v.get('statistics') or {}
                if not vid:
                    continue
                video_meta[vid] = snip
                rec_id = f'video:{vid}'
                if rec_id not in seen_ids:
                    metrics = {}
                    for src_k, dst_k in (('viewCount', 'views'), ('likeCount', 'likes'), ('commentCount', 'comments')):
                        if str(stats.get(src_k, '')).isdigit():
                            metrics[dst_k] = int(stats[src_k])
                    item = connectors.normalized(
                        'YouTube', rec_id, f'https://www.youtube.com/watch?v={vid}',
                        snip.get('title') or vid, snip.get('description') or snip.get('title') or '',
                        snip.get('publishedAt'),
                        fetch_method='official_api', content_kind='video', video_id=vid, channel_id=snip.get('channelId'),
                        retention_days=30, tags=[t for t in (snip.get('tags') or [])[:10] if t],
                        metrics=metrics or None,
                        ai_processing_authorized=ai_ok, ai_policy_note=policy_note,
                        attribution={'author': providers.text(snip.get('channelTitle'), 100), 'profile_url': f"https://www.youtube.com/channel/{snip['channelId']}" if snip.get('channelId') else None, 'license': 'YouTube Data API v3', 'source': 'YouTube'},
                    )
                    if item:
                        items.append(item)
                        newest = max(newest, item['observed_at'])

        # 3. Fetch channel metadata if requested (1 unit batched)
        if channel_ids and q.youtube_mode in ('channels', 'both'):
            reserve('youtube', 'core', s.youtube_workspace_daily_unit_limit, scope='workspace:' + org, cost=1)
            cdata = await gw.request(
                '/channels',
                params={'part': 'snippet,statistics,status', 'id': ','.join(channel_ids[:5]), 'key': api_key},
                ttl=900, bucket='core', capacity=s.youtube_daily_unit_limit, cost=1,
            )
            for ch in cdata.get('items') or []:
                cid = ch.get('id')
                snip = ch.get('snippet') or {}
                stats = ch.get('statistics') or {}
                rec_id = f'channel:{cid}'
                if not cid or rec_id in seen_ids:
                    continue
                metrics = {dst: int(stats[src]) for src, dst in (('subscriberCount', 'subscribers'), ('videoCount', 'videos'), ('viewCount', 'views')) if str(stats.get(src, '')).isdigit()}
                item = connectors.normalized(
                    'YouTube', rec_id, f'https://www.youtube.com/channel/{cid}',
                    snip.get('title') or cid, snip.get('description') or snip.get('title') or '',
                    snip.get('publishedAt'),
                    fetch_method='official_api', content_kind='channel', channel_id=cid,
                    retention_days=30, metrics=metrics or None,
                    ai_processing_authorized=ai_ok, ai_policy_note=policy_note,
                    attribution={'author': providers.text(snip.get('title'), 100), 'profile_url': f'https://www.youtube.com/channel/{cid}', 'license': 'YouTube Data API v3', 'source': 'YouTube'},
                )
                if item:
                    items.append(item)

        # 4. Fetch bounded public commentThreads & supported replies (graceful on COMMENTS_DISABLED)
        if q.youtube_comments and s.intent_radar_youtube_comments_enabled and video_ids:
            for vid in video_ids[:3]:
                if gw.client.requests >= 11:
                    break
                try:
                    reserve('youtube', 'core', s.youtube_workspace_daily_unit_limit, scope='workspace:' + org, cost=1)
                    threads = await gw.request(
                        '/commentThreads',
                        params={'part': 'snippet,replies', 'videoId': vid, 'maxResults': 5, 'order': 'relevance', 'textFormat': 'plainText', 'key': api_key},
                        ttl=300, bucket='core', capacity=s.youtube_daily_unit_limit, cost=1,
                    )
                except ProviderFailure as exc:
                    if exc.code in ('COMMENTS_DISABLED', 'CONTENT_UNAVAILABLE', 'PROVIDER_FORBIDDEN'):
                        comments_disabled_count += 1
                        continue
                    raise
                vtitle = (video_meta.get(vid) or {}).get('title') or f'YouTube video {vid}'
                vchannel = (video_meta.get(vid) or {}).get('channelId')
                for thread in (threads.get('items') or [])[:5]:
                    top = (thread.get('snippet') or {}).get('topLevelComment') or {}
                    top_id = top.get('id')
                    top_snip = top.get('snippet') or {}
                    if not top_id:
                        continue
                    rec_id = f'comment:{top_id}'
                    if rec_id not in seen_ids:
                        c_item = connectors.normalized(
                            'YouTube', rec_id, f'https://www.youtube.com/watch?v={vid}&lc={top_id}',
                            vtitle, top_snip.get('textDisplay') or top_snip.get('textOriginal') or '',
                            top_snip.get('publishedAt'),
                            fetch_method='official_api', content_kind='comment', video_id=vid, channel_id=vchannel,
                            parent_id=f'video:{vid}', depth=1, updated_at=top_snip.get('updatedAt'),
                            retention_days=30,
                            metrics={'likes': int(top_snip.get('likeCount') or 0), 'replies': int((thread.get('snippet') or {}).get('totalReplyCount') or 0)},
                            ai_processing_authorized=ai_ok, ai_policy_note=policy_note,
                            attribution={'author': providers.text(top_snip.get('authorDisplayName'), 100), 'profile_url': top_snip.get('authorChannelUrl'), 'license': 'YouTube Data API v3', 'source': 'YouTube'},
                        )
                        if c_item:
                            c_item['discussion_id'] = f'video:{vid}'
                            items.append(c_item)
                            newest = max(newest, c_item['observed_at'])
                    # Include inline or bounded replies (depth 2)
                    inline_replies = (thread.get('replies') or {}).get('comments') or []
                    for rep in inline_replies[:2]:
                        rep_id = rep.get('id')
                        rep_snip = rep.get('snippet') or {}
                        r_rec = f'comment:{rep_id}'
                        if not rep_id or r_rec in seen_ids:
                            continue
                        r_item = connectors.normalized(
                            'YouTube', r_rec, f'https://www.youtube.com/watch?v={vid}&lc={rep_id}',
                            vtitle, rep_snip.get('textDisplay') or rep_snip.get('textOriginal') or '',
                            rep_snip.get('publishedAt'),
                            fetch_method='official_api', content_kind='comment', video_id=vid, channel_id=vchannel,
                            parent_id=rec_id, depth=2, retention_days=30,
                            ai_processing_authorized=ai_ok, ai_policy_note=policy_note,
                            attribution={'author': providers.text(rep_snip.get('authorDisplayName'), 100), 'profile_url': rep_snip.get('authorChannelUrl'), 'license': 'YouTube Data API v3', 'source': 'YouTube'},
                        )
                        if r_item:
                            r_item['discussion_id'] = f'video:{vid}'
                            items.append(r_item)

        new_seen = list(dict.fromkeys([*(x['source_record_id'] for x in items), *seen_ids]))[:600]
        extra = f' ({comments_disabled_count} video(s) had comments disabled.)' if comments_disabled_count else ''
        return {
            'items': items[:q.result_limit],
            'requests': gw.client.requests,
            'scanned': len(items),
            'next_offset': None,
            'cursor': {'seen_ids': new_seen, 'published_after': newest or None},
            'coverage': f'Official YouTube Data API v3 ({q.youtube_mode}, comments={q.youtube_comments}) with fair-usage quotas, caching ({gw.cache_hits} hit(s)) and 30-day retention.{extra}',
        }
