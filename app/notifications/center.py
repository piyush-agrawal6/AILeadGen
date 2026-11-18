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
    if actor is None or org is None:
        ctx, _ = _require_member(c)
        actor = ctx.actor
        org = ctx.organization_id
    doc, _ = _load_prefs_doc(c, org)
    saved = (doc.get("user_notification_preferences") or {}).get(actor) or {}
    merged = {**DEFAULT_USER_PREFS, **{k: v for k, v in saved.items() if k != "categories"}}
    cats = {**DEFAULT_USER_PREFS["categories"], **(saved.get("categories") or {})}
    # Security and billing mandatory notices always remain enabled for account integrity
    cats["security"] = True
    cats["billing"] = True
    merged["categories"] = {k: bool(cats.get(k, True)) for k in CATEGORIES}
    from app.notifications import transactional as mail

    merged["email_delivery_available"] = bool(
        get_settings().transactional_mail_enabled and mail.configured()
    )
    return merged


def update_preferences(c, body: NotificationPreferencesUpdate) -> dict:
    ctx, _ = _require_member(c)
    org = ctx.organization_id
    actor = ctx.actor
    doc, exists = _load_prefs_doc(c, org)
    cats = {**DEFAULT_USER_PREFS["categories"], **{k: bool(v) for k, v in body.categories.items() if k in CATEGORIES}}
    cats["security"] = True
    cats["billing"] = True
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
    }
    all_user_prefs = dict(doc.get("user_notification_preferences") or {})
    all_user_prefs[actor] = user_pref
    doc["user_notification_preferences"] = all_user_prefs
    stamp = now()
    if exists:
        c.execute(
            "UPDATE intent_preferences SET configuration_json=?, revision=revision+1, updated_at=? WHERE organization_id=?",
            (json.dumps(doc), stamp, org),
        )
    else:
        base = {
            "default_view": "table",
            "min_relevance": 35,
            "topics": [],
            "alerts_enabled": True,
            "alert_threshold": 70,
            "source_retention_days": 30,
            **doc,
        }
        c.execute(
            "INSERT INTO intent_preferences(organization_id, configuration_json, revision, updated_at) VALUES(?,?,1,?)",
            (org, json.dumps(base), stamp),
        )
    return get_preferences(c, actor=actor, org=org)


def _encode_description(text: str, meta: dict) -> str:
    payload = {
        "text": text[:600],
        "category": meta.get("category", "monitoring"),
        "priority": meta.get("priority", "normal"),
        "url": meta.get("url") or "/intent-radar",
        "event_type": meta.get("event_type") or "WORKSPACE_EVENT",
        "recipient": meta.get("recipient"),
    }
    return META_PREFIX + json.dumps(payload, separators=(",", ":"))


def _decode_alert_row(row: dict) -> dict:
    raw_desc = str(row.get("description") or "")
    meta = {
        "text": raw_desc,
        "category": "monitoring" if row.get("monitor_id") else "signals",
        "priority": "normal",
        "url": f"/intent-radar/signals/{row['signal_id']}" if row.get("signal_id") else "/intent-radar/monitors" if row.get("monitor_id") else "/intent-radar",
        "event_type": "MONITOR_ALERT",
        "recipient": None,
    }
    if raw_desc.startswith(META_PREFIX):
        try:
            parsed = json.loads(raw_desc[len(META_PREFIX) :])
            if isinstance(parsed, dict):
                meta.update({k: v for k, v in parsed.items() if v is not None})
        except Exception:
            pass
    return {
        "id": row["id"],
        "kind": meta["event_type"],
        "category": meta["category"],
        "priority": meta["priority"],
        "title": row["title"],
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
        "INVITATION_ACCEPTED": ("Teammate joined workspace", "A team member accepted their workspace invitation.", "security", "normal", "/settings?category=team&tab=members"),
        "INVITATION_REJECTED": ("Invitation declined", "A pending workspace invitation was declined.", "security", "low", "/settings?category=team&tab=invitations"),
        "INTENT_RADAR": ("Monitor activity detected", "Scheduled Intent Radar monitoring recorded new activity.", "monitoring", "normal", "/intent-radar/monitors"),
    }
    title, desc, cat, prio, url = mapping.get(
        kind,
        ("Workspace update", "A workspace event was recorded.", "security", "low", "/intent-radar"),
    )
    return {
        "id": row["id"],
        "kind": kind,
        "category": cat,
        "priority": prio,
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
        if not (prefs.get("categories") or {}).get(category, True):
            return None
        if prefs.get("high_priority_only") and priority not in ("high", "urgent"):
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


def list_notifications(
    c,
    *,
    category: str | None = None,
    status: str = "all",
    priority: str | None = None,
    search: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    ctx, _ = _require_member(c)
    org = ctx.organization_id
    actor = ctx.actor

    items: list[dict] = []
    # 1. Workspace notifications targeted to this user
    for r in c.execute(
        "SELECT id,kind,entity_id,created_at,read_at,user_id FROM workspace_notifications WHERE organization_id=? AND user_id=? ORDER BY created_at DESC LIMIT 100",
        (org, actor),
    ).fetchall():
        items.append(_decode_workspace_notif(dict(r)))

    # 2. Rich workspace intent alerts (broadcast or targeted to this user)
    for r in c.execute(
        "SELECT id,monitor_id,signal_id,event_key,title,description,read_at,created_at FROM intent_alerts WHERE organization_id=? ORDER BY created_at DESC LIMIT 200",
        (org,),
    ).fetchall():
        decoded = _decode_alert_row(dict(r))
        if decoded.get("recipient") and decoded["recipient"] != actor:
            continue
        items.append(decoded)

    items.sort(key=lambda x: x["created_at"], reverse=True)
    unread_count = sum(1 for i in items if not i.get("read_at"))

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
        if q and q not in f"{item['title']} {item['description']} {item['category']}".casefold():
            continue
        filtered.append(item)

    total = len(filtered)
    start = max(0, (page - 1) * page_size)
    page_items = [
        {k: v for k, v in item.items() if k not in ("source_table", "recipient")}
        for item in filtered[start : start + page_size]
    ]
    return {
        "items": page_items,
        "unread_count": unread_count,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": start + page_size < total,
    }


def mark_read(c, notification_id: str) -> dict:
    ctx, _ = _require_member(c)
    org = ctx.organization_id
    actor = ctx.actor
    stamp = now()
    n1 = c.execute(
        "UPDATE intent_alerts SET read_at=COALESCE(read_at,?) WHERE organization_id=? AND id=?",
        (stamp, org, notification_id),
    ).rowcount
    n2 = c.execute(
        "UPDATE workspace_notifications SET read_at=COALESCE(read_at,?) WHERE organization_id=? AND user_id=? AND id=?",
        (stamp, org, actor, notification_id),
    ).rowcount
    if not (n1 or n2):
        raise HTTPException(404, "Notification not found.")
    return {"id": notification_id, "read_at": stamp}


def mark_all_read(c) -> dict:
    ctx, _ = _require_member(c)
    org = ctx.organization_id
    actor = ctx.actor
    stamp = now()
    n1 = c.execute(
        "UPDATE intent_alerts SET read_at=? WHERE organization_id=? AND read_at IS NULL",
        (stamp, org),
    ).rowcount
    n2 = c.execute(
        "UPDATE workspace_notifications SET read_at=? WHERE organization_id=? AND user_id=? AND read_at IS NULL",
        (stamp, org, actor),
    ).rowcount
    return {"marked_read": int(n1) + int(n2), "read_at": stamp}


def send_test_email(c) -> dict:
    ctx, role = _require_member(c)
    if role not in ("OWNER", "ADMIN"):
        raise HTTPException(403, "Only workspace owners or admins can send a test notification email.")
    from app.accounts import security
    from app.notifications import dispatch, transactional as mail

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
    dispatch.enqueue_notification(nid)
    return {"queued": True, "notification_id": nid, "recipient": ctx.actor}
