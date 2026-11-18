"""Centralized workspace notification center, preferences, deduplication, and Resend email alerts."""
from __future__ import annotations

import json
import time
import uuid
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.api.organization import membership_role
from app.config.settings import get_settings
from app.database.prospects import now
from app.platform.context import current

CATEGORIES = ("discovery", "signals", "opportunities", "monitoring", "ai", "billing", "security")
PRIORITIES = ("low", "normal", "high", "urgent")
META_PREFIX = "__pb_notif__:"

DEFAULT_USER_PREFS = {
    "in_app_enabled": True,
    "email_enabled": True,
    "email_cadence": "immediate",
    "high_priority_only": False,
    "timezone": "UTC",
    "quiet_hours_enabled": False,
    "quiet_hours_start": "22:00",
    "quiet_hours_end": "07:00",
    "categories": {
        "discovery": True,
        "signals": True,
        "opportunities": True,
        "monitoring": True,
        "ai": True,
        "billing": True,
        "security": True,
    },
}


class NotificationPreferencesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    in_app_enabled: bool = True
    email_enabled: bool = True
    email_cadence: Literal["immediate", "daily_digest", "weekly_digest", "off"] = "immediate"
    high_priority_only: bool = False
    timezone: str = Field("UTC", min_length=2, max_length=64)
    quiet_hours_enabled: bool = False
    quiet_hours_start: str = Field("22:00", pattern=r"^\d{2}:\d{2}$")
    quiet_hours_end: str = Field("07:00", pattern=r"^\d{2}:\d{2}$")
    categories: dict[str, bool] = Field(default_factory=dict)
    email_categories: dict[str, bool] | None = None


def _in_quiet_hours(prefs: dict) -> bool:
    if not prefs.get("quiet_hours_enabled"):
        return False
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(str(prefs.get("timezone") or "UTC"))
        now_local = datetime.now(tz)
        cur = now_local.hour * 60 + now_local.minute
        sh, sm = (int(x) for x in str(prefs.get("quiet_hours_start") or "22:00").split(":"))
        eh, em = (int(x) for x in str(prefs.get("quiet_hours_end") or "07:00").split(":"))
        start = sh * 60 + sm
        end = eh * 60 + em
        if start == end:
            return False
        if start < end:
            return start <= cur < end
        return cur >= start or cur < end
    except Exception:
        return False


def _require_member(c):
    ctx = current()
    role = membership_role(c, ctx.actor, ctx.organization_id)
    if not role:
        raise HTTPException(403, "Active workspace membership required.")
    return ctx, role


def _load_prefs_doc(c, org: str) -> tuple[dict, bool]:
    row = c.execute(
        "SELECT configuration_json FROM intent_preferences WHERE organization_id=?",
        (org,),
    ).fetchone()
    if not row or not row["configuration_json"]:
        return {}, False
    try:
        return json.loads(row["configuration_json"]), True
    except Exception:
        return {}, True


def get_preferences(c, *, actor: str | None = None, org: str | None = None) -> dict:
    role = None
    if actor is None or org is None:
        ctx, role = _require_member(c)
        actor = ctx.actor
        org = ctx.organization_id
    else:
        role = membership_role(c, actor, org)
    doc, _ = _load_prefs_doc(c, org)
    saved = (doc.get("user_notification_preferences") or {}).get(actor) or {}
    merged = {**DEFAULT_USER_PREFS, **{k: v for k, v in saved.items() if k not in ("categories", "email_categories")}}
    cats = {**DEFAULT_USER_PREFS["categories"], **(saved.get("categories") or {})}
    # Security and billing mandatory notices always remain enabled for account integrity
    cats["security"] = True
    cats["billing"] = True
    merged["categories"] = {k: bool(cats.get(k, True)) for k in CATEGORIES}
    email_cats = {**merged["categories"], **(saved.get("email_categories") or {})}
    email_cats["security"] = True
    email_cats["billing"] = True
    merged["email_categories"] = {k: bool(email_cats.get(k, True)) for k in CATEGORIES}
    from app.notifications import transactional as mail

    merged["email_delivery_available"] = bool(
        get_settings().transactional_mail_enabled and mail.configured()
    )
    merged["can_send_test_email"] = role in ("OWNER", "ADMIN")
    return merged


def update_preferences(c, body: NotificationPreferencesUpdate) -> dict:
    ctx, _ = _require_member(c)
    org = ctx.organization_id
    actor = ctx.actor
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo(body.timezone)
    except Exception:
        raise HTTPException(422, "Choose a valid IANA timezone.") from None
    doc, exists = _load_prefs_doc(c, org)
    cats = {**DEFAULT_USER_PREFS["categories"], **{k: bool(v) for k, v in body.categories.items() if k in CATEGORIES}}
    cats["security"] = True
    cats["billing"] = True
    email_cats = (
        {**cats, **{k: bool(v) for k, v in body.email_categories.items() if k in CATEGORIES}}
        if body.email_categories is not None
        else dict(cats)
    )
    email_cats["security"] = True
    email_cats["billing"] = True
    user_pref = {
        "in_app_enabled": body.in_app_enabled,
        "email_enabled": body.email_enabled,
        "email_cadence": body.email_cadence,
        "high_priority_only": body.high_priority_only,
        "timezone": body.timezone,
        "quiet_hours_enabled": body.quiet_hours_enabled,
        "quiet_hours_start": body.quiet_hours_start,
        "quiet_hours_end": body.quiet_hours_end,
        "categories": cats,
        "email_categories": email_cats,
    }
    all_user_prefs = dict(doc.get("user_notification_preferences") or {})
    all_user_prefs[actor] = user_pref
    doc["user_notification_preferences"] = all_user_prefs
    stamp = now()
    if exists:
        # Preserve workspace intent_preferences.revision so saving personal notification
        # preferences never triggers spurious 409 conflicts on workspace Research Preferences.
        c.execute(
            "UPDATE intent_preferences SET configuration_json=?, updated_at=? WHERE organization_id=?",
            (json.dumps(doc), stamp, org),
        )
    else:
        base = {
            "default_view": "table",
            "min_relevance": 0,
            "topics": [],
            "alerts_enabled": True,
            "alert_threshold": 85,
            "source_retention_days": 30,
            **doc,
        }
        c.execute(
            "INSERT INTO intent_preferences(organization_id, configuration_json, revision, updated_at) VALUES(?,?,0,?)",
            (org, json.dumps(base), stamp),
        )
    return get_preferences(c, actor=actor, org=org)


def _severity_for(event_type: str, priority: str, title: str = "") -> str:
    ev = (event_type or "").upper()
    t = (title or "").casefold()
    if any(tok in ev for tok in ("FAILED", "FAILURE", "ERROR", "REVOKED", "SUSPENDED")) or any(
        tok in t for tok in ("failed", "error", "could not complete")
    ):
        return "error"
    if priority == "urgent":
        return "error"
    if (
        priority == "high"
        or any(tok in ev for tok in ("UNAVAILABLE", "QUOTA", "LIMIT", "WARNING", "EXPIR", "DECLINED"))
        or any(tok in t for tok in ("unavailable", "warning", "limit", "quota"))
    ):
        return "warning"
    if any(tok in ev for tok in ("COMPLETED", "CREATED", "ACCEPTED", "VERIFIED", "APPROVED", "ACTIVATED")) or any(
        tok in t for tok in ("completed", "created", "joined", "verified")
    ):
        return "success"
    return "info"


def _encode_description(text: str, meta: dict) -> str:
    payload = {
        "text": text[:600],
        "category": meta.get("category", "monitoring"),
        "priority": meta.get("priority", "normal"),
        "url": meta.get("url") or "/intent-radar",
        "event_type": meta.get("event_type") or "WORKSPACE_EVENT",
        "recipient": meta.get("recipient"),
        "severity": meta.get("severity") or _severity_for(meta.get("event_type") or "", meta.get("priority", "normal")),
    }
    return META_PREFIX + json.dumps(payload, separators=(",", ":"))


def redact_signal_alerts(c, organization_id: str, signal_id: str) -> None:
    """Redact withdrawn/expired public source text on signal alerts while preserving notification metadata."""
    rows = c.execute(
        "SELECT id, description FROM intent_alerts WHERE organization_id=? AND signal_id=?",
        (organization_id, signal_id),
    ).fetchall()
    for row in rows:
        raw_desc = str(row["description"] or "")
        if raw_desc.startswith(META_PREFIX):
            try:
                parsed = json.loads(raw_desc[len(META_PREFIX) :])
                if isinstance(parsed, dict):
                    parsed["text"] = "Source content unavailable"
                    c.execute(
                        "UPDATE intent_alerts SET description=? WHERE organization_id=? AND id=?",
                        (META_PREFIX + json.dumps(parsed, separators=(",", ":")), organization_id, row["id"]),
                    )
                    continue
            except Exception:
                pass
        c.execute(
            "UPDATE intent_alerts SET description='Source content unavailable' WHERE organization_id=? AND id=?",
            (organization_id, row["id"]),
        )


def _decode_alert_row(row: dict) -> dict:
    raw_desc = str(row.get("description") or "")
    event_key = str(row.get("event_key") or "")
    title = str(row.get("title") or "")
    monitor_id = row.get("monitor_id")
    signal_id = row.get("signal_id")

    if raw_desc.startswith(META_PREFIX):
        meta = {
            "text": "",
            "category": "monitoring" if monitor_id else "signals",
            "priority": "normal",
            "url": (
                f"/intent-radar/signals/{signal_id}"
                if signal_id
                else f"/intent-radar/monitors/{monitor_id}"
                if monitor_id
                else "/intent-radar"
            ),
            "event_type": "WORKSPACE_EVENT",
            "recipient": None,
            "severity": None,
        }
        try:
            parsed = json.loads(raw_desc[len(META_PREFIX) :])
            if isinstance(parsed, dict):
                meta.update({k: v for k, v in parsed.items() if v is not None})
        except Exception:
            pass
    else:
        # Legacy / plain-text intent_alerts classification (never misclassify ad-hoc discovery failures as Signals or Monitors)
        is_job_failure = event_key.startswith("job-failure:")
        is_source_failure = event_key.startswith("source-failure:")
        if is_job_failure or is_source_failure:
            if monitor_id:
                category = "monitoring"
                event_type = "MONITOR_CHECK_FAILED" if is_job_failure else "MONITOR_SOURCE_FAILED"
                url = f"/intent-radar/monitors/{monitor_id}"
            else:
                category = "discovery"
                event_type = "DISCOVERY_FAILED" if is_job_failure else "DISCOVERY_SOURCE_FAILED"
                url = "/intent-radar/discover/history"
                if title == "Intent monitor check failed":
                    title = "Discovery search failed"
            priority = "high"
        elif monitor_id:
            category = "monitoring"
            event_type = "MONITOR_MATCH"
            priority = "high" if "high-relevance" in title.casefold() else "normal"
            url = f"/intent-radar/signals/{signal_id}" if signal_id else f"/intent-radar/monitors/{monitor_id}"
        elif signal_id:
            category = "signals"
            event_type = "SIGNAL_ALERT"
            priority = "normal"
            url = f"/intent-radar/signals/{signal_id}"
        else:
            category = "discovery"
            event_type = "DISCOVERY_EVENT"
            priority = "normal"
            url = "/intent-radar/discover/history"
        meta = {
            "text": raw_desc,
            "category": category,
            "priority": priority,
            "url": url,
            "event_type": event_type,
            "recipient": None,
            "severity": None,
        }

    severity = meta.get("severity") or _severity_for(meta["event_type"], meta["priority"], title)
    return {
        "id": row["id"],
        "entity_id": row["id"],
        "kind": meta["event_type"],
        "category": meta["category"],
        "priority": meta["priority"],
        "severity": severity,
        "title": title,
        "description": meta["text"],
        "url": meta["url"],
        "read_at": row.get("read_at"),
        "created_at": row["created_at"],
        "source_table": "intent_alerts",
        "recipient": meta.get("recipient"),
    }


def _decode_workspace_notif(row: dict) -> dict:
    kind = str(row.get("kind") or "WORKSPACE_UPDATE")
    mapping = {
        "INVITATION_ACCEPTED": (
            "Teammate joined workspace",
            "A team member accepted their workspace invitation.",
            "security",
            "normal",
            "success",
            "/settings?category=team&tab=members",
        ),
        "INVITATION_REJECTED": (
            "Invitation declined",
            "A pending workspace invitation was declined.",
            "security",
            "low",
            "warning",
            "/settings?category=team&tab=invitations",
        ),
        "INTENT_RADAR": (
            "Intent Radar activity recorded",
            "Intent Radar recorded new workspace activity.",
            "discovery",
            "normal",
            "info",
            "/intent-radar",
        ),
    }
    title, desc, cat, prio, sev, url = mapping.get(
        kind,
        ("Workspace update", "A workspace event was recorded.", "security", "low", "info", "/intent-radar"),
    )
    return {
        "id": row["id"],
        "entity_id": row.get("entity_id"),
        "kind": kind,
        "category": cat,
        "priority": prio,
        "severity": sev,
        "title": title,
        "description": desc,
        "url": url,
        "read_at": row.get("read_at"),
        "created_at": row["created_at"],
        "source_table": "workspace_notifications",
        "recipient": row.get("user_id"),
    }


def emit(
    c,
    organization_id: str,
    *,
    category: str,
    event_type: str,
    title: str,
    description: str,
    priority: str = "normal",
    resource_url: str | None = None,
    dedupe_key: str | None = None,
    monitor_id: str | None = None,
    signal_id: str | None = None,
    recipient_email: str | None = None,
    send_email: bool = False,
) -> str | None:
    """Persist an idempotent, workspace-scoped notification and optionally queue a Resend email."""
    cat = category if category in CATEGORIES else "signals"
    prio = priority if priority in PRIORITIES else "normal"
    key = str(uuid.uuid4())
    ev_key = (dedupe_key or f"{cat}:{event_type}:{key}")[:180]
    stamp = now()
    encoded = _encode_description(
        description,
        {
            "category": cat,
            "priority": prio,
            "url": resource_url or "/intent-radar",
            "event_type": event_type,
            "recipient": recipient_email,
        },
    )
    try:
        inserted = c.execute(
            "INSERT INTO intent_alerts(id,organization_id,monitor_id,signal_id,event_key,title,description,created_at) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(organization_id,event_key) DO NOTHING",
            (key, organization_id, monitor_id, signal_id, ev_key, title[:200], encoded, stamp),
        ).rowcount
    except Exception:
        return None
    if not inserted:
        return None

    if send_email and recipient_email:
        _maybe_queue_email(
            c,
            organization_id=organization_id,
            recipient_email=recipient_email,
            category=cat,
            priority=prio,
            title=title,
            description=description,
            resource_url=resource_url or "/notifications",
            dedupe_key=f"email:{organization_id}:{ev_key}",
            authority_id=key,
        )
    return key


def _maybe_queue_email(
    c,
    *,
    organization_id: str,
    recipient_email: str,
    category: str,
    priority: str,
    title: str,
    description: str,
    resource_url: str,
    dedupe_key: str,
    authority_id: str,
):
    from app.notifications import transactional as mail

    if not get_settings().transactional_mail_enabled or not mail.configured():
        return None
    prefs = get_preferences(c, actor=recipient_email, org=organization_id)
    mandatory = category in ("security", "billing") and priority in ("high", "urgent")
    if not mandatory:
        if not prefs.get("email_enabled") or prefs.get("email_cadence") != "immediate":
            return None
        email_cats = prefs.get("email_categories") or prefs.get("categories") or {}
        if not email_cats.get(category, True):
            return None
        if prefs.get("high_priority_only") and priority not in ("high", "urgent"):
            return None
        if _in_quiet_hours(prefs):
            return None
    try:
        nid = mail.queue(
            c,
            recipient_email,
            "NOTIFICATION_ALERT",
            authority_id,
            {
                "title": title[:160],
                "summary": description[:1200],
                "category": category,
                "url": resource_url if resource_url.startswith("/") else "/notifications",
                "optional": not mandatory,
            },
            dedupe_key=dedupe_key[:200],
            expires_at=int(time.time()) + 86400,
            organization_id=organization_id,
        )
        return nid
    except Exception:
        return None


def _collect_visible_notifications(c, org: str, actor: str) -> list[dict]:
    """Return deduplicated, actor-visible notifications across intent_alerts and workspace_notifications."""
    ws_rows = [
        dict(r)
        for r in c.execute(
            "SELECT id,kind,entity_id,created_at,read_at,user_id FROM workspace_notifications "
            "WHERE organization_id=? AND user_id=? ORDER BY created_at DESC LIMIT 200",
            (org, actor),
        ).fetchall()
    ]
    alert_rows = [
        dict(r)
        for r in c.execute(
            "SELECT id,monitor_id,signal_id,event_key,title,description,read_at,created_at FROM intent_alerts "
            "WHERE organization_id=? ORDER BY created_at DESC LIMIT 300",
            (org,),
        ).fetchall()
    ]

    # Map workspace_notifications(INTENT_RADAR) by entity_id so we NEVER double-list or double-count
    ws_radar_by_entity: dict[str, dict] = {}
    items: list[dict] = []
    for r in ws_rows:
        if r.get("kind") == "INTENT_RADAR" and r.get("entity_id"):
            ws_radar_by_entity[str(r["entity_id"])] = r
        else:
            items.append(_decode_workspace_notif(r))

    seen_alert_ids: set[str] = set()
    for r in alert_rows:
        decoded = _decode_alert_row(r)
        if decoded.get("recipient") and decoded["recipient"] != actor:
            continue
        aid = str(decoded["id"])
        seen_alert_ids.add(aid)
        paired_ws = ws_radar_by_entity.get(aid)
        if paired_ws and paired_ws.get("read_at") and not decoded.get("read_at"):
            decoded["read_at"] = paired_ws["read_at"]
        items.append(decoded)

    # For any legacy workspace_notifications(INTENT_RADAR) whose entity_id was outside the 300-row window,
    # check if it exists in intent_alerts; skip duplicates and only keep genuine orphan records.
    orphan_entities = [eid for eid in ws_radar_by_entity if eid not in seen_alert_ids]
    if orphan_entities:
        placeholders = ",".join("?" for _ in orphan_entities)
        existing_ids = {
            str(r["id"])
            for r in c.execute(
                f"SELECT id FROM intent_alerts WHERE organization_id=? AND id IN ({placeholders})",
                [org, *orphan_entities],
            ).fetchall()
        }
        for eid in orphan_entities:
            if eid not in existing_ids:
                items.append(_decode_workspace_notif(ws_radar_by_entity[eid]))

    items.sort(key=lambda x: x["created_at"], reverse=True)
    return items


def list_notifications(
    c,
    *,
    category: str | None = None,
    status: str = "all",
    priority: str | None = None,
    severity: str | None = None,
    search: str = "",
    from_date: str | None = None,
    to_date: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    ctx, _ = _require_member(c)
    org = ctx.organization_id
    actor = ctx.actor

    items = _collect_visible_notifications(c, org, actor)
    unread_count = sum(1 for i in items if not i.get("read_at"))

    category_counts: dict[str, int] = {"all": len(items), **{cat: 0 for cat in CATEGORIES}}
    unread_by_category: dict[str, int] = {"all": unread_count, **{cat: 0 for cat in CATEGORIES}}
    for item in items:
        cat = item.get("category") or "signals"
        if cat in category_counts:
            category_counts[cat] += 1
            if not item.get("read_at"):
                unread_by_category[cat] += 1

    q = search.strip().casefold()
    filtered = []
    for item in items:
        if category and category != "all" and item["category"] != category:
            continue
        if status == "unread" and item.get("read_at"):
            continue
        if status == "read" and not item.get("read_at"):
            continue
        if priority and priority != "all" and item["priority"] != priority:
            continue
        if severity and severity != "all" and item.get("severity") != severity:
            continue
        if from_date and str(item["created_at"])[:10] < from_date[:10]:
            continue
        if to_date and str(item["created_at"])[:10] > to_date[:10]:
            continue
        if q and q not in f"{item['title']} {item['description']} {item['category']} {item['kind']}".casefold():
            continue
        filtered.append(item)

    total = len(filtered)
    start = max(0, (page - 1) * page_size)
    page_items = [
        {k: v for k, v in item.items() if k not in ("source_table", "recipient", "entity_id")}
        for item in filtered[start : start + page_size]
    ]
    return {
        "items": page_items,
        "unread_count": unread_count,
        "category_counts": category_counts,
        "unread_by_category": unread_by_category,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": start + page_size < total,
    }


def _set_read_state(c, org: str, actor: str, notification_id: str, read: bool) -> bool:
    stamp = now() if read else None
    updated = False
    row = c.execute(
        "SELECT id,monitor_id,signal_id,event_key,title,description,read_at,created_at FROM intent_alerts WHERE organization_id=? AND id=?",
        (org, notification_id),
    ).fetchone()
    if row:
        decoded = _decode_alert_row(dict(row))
        if decoded.get("recipient") and decoded["recipient"] != actor:
            return False
        c.execute(
            "UPDATE intent_alerts SET read_at=? WHERE organization_id=? AND id=?",
            (stamp, org, notification_id),
        )
        c.execute(
            "UPDATE workspace_notifications SET read_at=? WHERE organization_id=? AND user_id=? AND entity_id=?",
            (stamp, org, actor, notification_id),
        )
        updated = True

    ws = c.execute(
        "SELECT id,entity_id FROM workspace_notifications WHERE organization_id=? AND user_id=? AND id=?",
        (org, actor, notification_id),
    ).fetchone()
    if ws:
        c.execute(
            "UPDATE workspace_notifications SET read_at=? WHERE organization_id=? AND user_id=? AND id=?",
            (stamp, org, actor, notification_id),
        )
        if ws["entity_id"]:
            linked = c.execute(
                "SELECT id,monitor_id,signal_id,event_key,title,description,read_at,created_at FROM intent_alerts WHERE organization_id=? AND id=?",
                (org, ws["entity_id"]),
            ).fetchone()
            if linked:
                dec = _decode_alert_row(dict(linked))
                if not dec.get("recipient") or dec["recipient"] == actor:
                    c.execute(
                        "UPDATE intent_alerts SET read_at=? WHERE organization_id=? AND id=?",
                        (stamp, org, ws["entity_id"]),
                    )
        updated = True
    return updated


def mark_read(c, notification_id: str) -> dict:
    ctx, _ = _require_member(c)
    if not _set_read_state(c, ctx.organization_id, ctx.actor, notification_id, True):
        raise HTTPException(404, "Notification not found.")
    return {"id": notification_id, "read_at": now()}


def mark_unread(c, notification_id: str) -> dict:
    ctx, _ = _require_member(c)
    if not _set_read_state(c, ctx.organization_id, ctx.actor, notification_id, False):
        raise HTTPException(404, "Notification not found.")
    return {"id": notification_id, "read_at": None}


class BulkNotificationAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ids: list[str] = Field(min_length=1, max_length=100)
    action: Literal["read", "unread"] = "read"


def bulk_update(c, body: BulkNotificationAction) -> dict:
    ctx, _ = _require_member(c)
    org = ctx.organization_id
    actor = ctx.actor
    want_read = body.action == "read"
    succeeded = 0
    failed: list[str] = []
    for nid in dict.fromkeys(body.ids):
        if _set_read_state(c, org, actor, nid, want_read):
            succeeded += 1
        else:
            failed.append(nid)
    return {"updated": succeeded, "failed": failed, "action": body.action}


def mark_all_read(c, *, category: str | None = None) -> dict:
    ctx, _ = _require_member(c)
    org = ctx.organization_id
    actor = ctx.actor
    stamp = now()
    visible = _collect_visible_notifications(c, org, actor)
    targets = [
        item
        for item in visible
        if not item.get("read_at") and (not category or category == "all" or item.get("category") == category)
    ]
    marked = 0
    for item in targets:
        if _set_read_state(c, org, actor, item["id"], True):
            marked += 1
    return {"marked_read": marked, "read_at": stamp}


def send_test_email(c) -> dict:
    ctx, role = _require_member(c)
    if role not in ("OWNER", "ADMIN"):
        raise HTTPException(403, "Only workspace owners or admins can send a test notification email.")
    from app.accounts import security
    from app.notifications import transactional as mail

    if not get_settings().transactional_mail_enabled or not mail.configured():
        raise HTTPException(503, "Transactional email delivery (Resend) is not configured in this environment.")
    if security.limited(c, "notification-test-email", ctx.actor, 3, 3600):
        raise HTTPException(429, "Test email limit reached (3 per hour). Please try again later.")

    nid = mail.queue(
        c,
        ctx.actor,
        "NOTIFICATION_ALERT",
        ctx.organization_id,
        {
            "title": "PlaneByte Notification Email Verified",
            "summary": "This test confirms that PlaneByte transactional email notifications are configured and delivering properly for your workspace.",
            "category": "security",
            "url": "/notifications",
            "optional": True,
        },
        dedupe_key=f"test-email:{ctx.actor}:{int(time.time())}",
        expires_at=int(time.time()) + 3600,
        organization_id=ctx.organization_id,
    )
    c.commit()
    # Perform synchronous bounded delivery so the caller receives honest delivery
    # confirmation (provider acceptance ID) or an actionable failure reason.
    try:
        mail.deliver(nid)
    except Exception as exc:
        raise HTTPException(502, f"Test email delivery failed: {str(exc)[:180]}") from None

    row = c.execute(
        "SELECT status, provider_message_id, error_code FROM transactional_notifications WHERE id=?",
        (nid,),
    ).fetchone()
    status = row["status"] if row else "UNKNOWN"
    err = row["error_code"] if row else None
    provider_id = row["provider_message_id"] if row else None
    if status in ("ACCEPTED", "DELIVERED"):
        return {
            "delivered": True,
            "queued": True,
            "status": status,
            "notification_id": nid,
            "provider_message_id": provider_id,
            "recipient": ctx.actor,
        }
    if status == "CANCELLED":
        raise HTTPException(409, "Test email could not be delivered because this address is suppressed or not authorized for transactional mail.")
    if err == "DAILY_DELIVERY_LIMIT":
        raise HTTPException(429, "Platform daily transactional email limit has been reached. Try again after 00:00 UTC.")
    if status == "QUEUED" and err == "DELIVERY_RETRY_PENDING":
        raise HTTPException(503, "Email provider temporarily unavailable; delivery is queued for automatic retry.")
    raise HTTPException(502, f"Email provider rejected the test delivery ({err or status}). Verify Resend domain & sender settings.")
