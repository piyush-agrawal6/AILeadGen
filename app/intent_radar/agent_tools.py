"""Typed, tenant-isolated, policy-enforcing tool registry for the PlaneByte Workspace AI Agent.

Read tools query authorized workspace data directly with ZERO AI quota consumption.
Write/action tools ALWAYS require explicit user confirmation via typed action proposals,
enforce workspace RBAC, preserve idempotency, log to audit_log, and emit notifications.
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.api.organization import membership_role
from app.config.settings import get_settings
from app.database.prospects import now
from app.growth_intelligence import analytics
from app.intent_radar import models as radar_models
from app.intent_radar import service as radar

# ---------------------------------------------------------------------------
# Tool Metadata Registry (for UI transparency, prompt grounding & validation)
# ---------------------------------------------------------------------------

READ_TOOLS: dict[str, dict[str, Any]] = {
    "get_workspace_summary": {
        "label": "Workspace overview",
        "kind": "read",
        "description": "Fetch live workspace counts across signals, discoveries, ICPs, monitors, opportunities, and notifications.",
    },
    "search_signals": {
        "label": "Search intent signals",
        "kind": "read",
        "description": "Search and filter workspace intent signals by keyword, source, status, or minimum score.",
    },
    "get_signal_detail": {
        "label": "Inspect signal detail",
        "kind": "read",
        "description": "Read full details, evidence provenance, and AI source-policy status for a specific signal.",
    },
    "list_discoveries": {
        "label": "Recent discoveries",
        "kind": "read",
        "description": "List recent discovery runs, match counts, statuses, and sources.",
    },
    "list_icps": {
        "label": "Ideal Customer Profiles",
        "kind": "read",
        "description": "List all workspace ICPs including primary ICP, targeting criteria, and related signal counts.",
    },
    "compare_icps_with_signals": {
        "label": "Compare & prioritize ICPs",
        "kind": "read",
        "description": "Compare workspace ICPs against real collected signals and profile completeness.",
    },
    "list_monitors": {
        "label": "Monitoring rules",
        "kind": "read",
        "description": "List active, paused, and draft Intent Radar monitors with schedules.",
    },
    "list_opportunities": {
        "label": "Opportunities pipeline",
        "kind": "read",
        "description": "List tracked intent opportunities, priorities, statuses, and next actions.",
    },
    "get_sources_health": {
        "label": "Sources & AI policy status",
        "kind": "read",
        "description": "Inspect enabled data sources, custom feeds, and external source AI processing policies.",
    },
    "get_billing_usage": {
        "label": "Plan & usage allowances",
        "kind": "read",
        "description": "Inspect current plan, trial status, and remaining monthly search & AI operation allowances.",
    },
    "list_notifications": {
        "label": "Recent notifications",
        "kind": "read",
        "description": "Inspect unread and recent workspace alerts and system notifications.",
    },
    "search_research_library": {
        "label": "Research library & saved searches",
        "kind": "read",
        "description": "Inspect saved bookmarks and reusable saved discovery templates.",
    },
}

WRITE_TOOLS: dict[str, dict[str, Any]] = {
    "create_icp": {
        "label": "Create Ideal Customer Profile",
        "kind": "write",
        "requires_confirmation": True,
        "required_roles": ("OWNER", "ADMIN"),
        "quota_note": "No search or AI quota consumed.",
    },
    "update_icp": {
        "label": "Update Ideal Customer Profile",
        "kind": "write",
        "requires_confirmation": True,
        "required_roles": ("OWNER", "ADMIN"),
        "quota_note": "No search or AI quota consumed.",
    },
    "set_primary_icp": {
        "label": "Set Primary ICP",
        "kind": "write",
        "requires_confirmation": True,
        "required_roles": ("OWNER", "ADMIN"),
        "quota_note": "No search or AI quota consumed.",
    },
    "save_search": {
        "label": "Save Reusable Discovery Search",
        "kind": "write",
        "requires_confirmation": True,
        "required_roles": ("OWNER", "ADMIN", "MEMBER"),
        "quota_note": "No search quota consumed until you run it.",
    },
    "run_discovery": {
        "label": "Run Discovery Search",
        "kind": "write",
        "requires_confirmation": True,
        "required_roles": ("OWNER", "ADMIN", "MEMBER"),
        "quota_note": "Consumes 1 monthly discovery search allowance when executed.",
    },
    "create_monitor": {
        "label": "Create Intent Monitor",
        "kind": "write",
        "requires_confirmation": True,
        "required_roles": ("OWNER", "ADMIN", "MEMBER"),
        "quota_note": "Uses 1 active monitor slot if created Active.",
    },
    "toggle_monitor": {
        "label": "Pause or Resume Monitor",
        "kind": "write",
        "requires_confirmation": True,
        "required_roles": ("OWNER", "ADMIN", "MEMBER"),
        "quota_note": "Resuming uses 1 active monitor slot.",
    },
    "save_signal": {
        "label": "Save Signal to Research Library",
        "kind": "write",
        "requires_confirmation": True,
        "required_roles": ("OWNER", "ADMIN", "MEMBER"),
        "quota_note": "No quota consumed.",
    },
    "update_signal_status": {
        "label": "Update Signal Review Status",
        "kind": "write",
        "requires_confirmation": True,
        "required_roles": ("OWNER", "ADMIN", "MEMBER"),
        "quota_note": "No quota consumed.",
    },
    "create_opportunity": {
        "label": "Create Opportunity from Signal",
        "kind": "write",
        "requires_confirmation": True,
        "required_roles": ("OWNER", "ADMIN", "MEMBER"),
        "quota_note": "Counts toward workspace opportunity allowance.",
    },
    "update_opportunity": {
        "label": "Update Opportunity",
        "kind": "write",
        "requires_confirmation": True,
        "required_roles": ("OWNER", "ADMIN", "MEMBER"),
        "quota_note": "No quota consumed.",
    },
}


# ---------------------------------------------------------------------------
# Typed Action Payloads
# ---------------------------------------------------------------------------

class CreateIcpParams(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=120)
    description: str = Field("", max_length=1000)
    industries: list[str] = Field(default_factory=list, max_length=12)
    pain_points: list[str] = Field(default_factory=list, max_length=12)
    business_needs: list[str] = Field(default_factory=list, max_length=12)
    keywords: list[str] = Field(default_factory=list, max_length=15)
    competitors: list[str] = Field(default_factory=list, max_length=10)
    exclusions: list[str] = Field(default_factory=list, max_length=10)
    set_as_primary: bool = False


class SetPrimaryIcpParams(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    icp_id: str = Field(min_length=10, max_length=64)


class SaveSearchParams(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=120)
    description: str = Field("", max_length=500)
    keywords: list[str] = Field(min_length=1, max_length=12)
    sources: list[str] = Field(default_factory=lambda: ["hacker_news", "github", "stack_exchange"], max_length=10)
    min_relevance: int = Field(45, ge=0, le=100)


class RunDiscoveryParams(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    title: str = Field("", max_length=120)
    keywords: list[str] = Field(min_length=1, max_length=12)
    sources: list[str] = Field(default_factory=lambda: ["hacker_news", "github", "stack_exchange"], max_length=10)
    min_relevance: int = Field(45, ge=0, le=100)
    icp_id: str | None = None


class CreateMonitorParams(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=120)
    description: str = Field("", max_length=500)
    goal: str = Field("Track buying conversations", max_length=200)
    keywords: list[str] = Field(min_length=1, max_length=12)
    sources: list[str] = Field(default_factory=lambda: ["hacker_news", "github"], max_length=10)
    status: Literal["Active", "Paused", "Draft"] = "Active"


class ToggleMonitorParams(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    monitor_id: str = Field(min_length=10, max_length=64)
    status: Literal["Active", "Paused"]


class SaveSignalParams(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    signal_id: str = Field(min_length=10, max_length=64)


class UpdateSignalStatusParams(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    signal_id: str = Field(min_length=10, max_length=64)
    status: Literal["Reviewed", "Saved", "Qualified", "Dismissed"]
    notes: str | None = Field(None, max_length=2000)


class CreateOpportunityParams(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    signal_id: str = Field(min_length=10, max_length=64)
    priority: Literal["Low", "Medium", "High"] = "Medium"
    notes: str = Field("", max_length=1000)
    next_action: str = Field("Review context", max_length=200)


class UpdateOpportunityParams(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)
    opportunity_id: str = Field(min_length=10, max_length=64)
    status: Literal["Saved", "Reviewing", "Qualified", "Closed"] = "Reviewing"
    priority: Literal["Low", "Medium", "High"] = "Medium"
    notes: str = Field("", max_length=1000)
    next_action: str = Field("Follow up on signal research", max_length=200)


# ---------------------------------------------------------------------------
# Read Tool Implementations (Zero AI Quota, Strictly Tenant-Scoped)
# ---------------------------------------------------------------------------

def _allowed_sources(c) -> set[str]:
    from app.intent_radar import connectors
    return {s["id"] for s in connectors.catalog(c) if s.get("selectable") or s.get("state") in ("READY", "CONFIGURED", "CONNECTED")}


def execute_read_tool(c, tool_name: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute an authorized workspace read tool. Never mutates state or consumes AI quota."""
    ctx = analytics.access(c)
    org = ctx.organization_id
    p = params or {}

    if tool_name == "get_workspace_summary":
        ov = radar.overview(c, include_previews=False)
        total_signals = int(c.execute("SELECT COUNT(*) FROM intent_signals WHERE organization_id=? AND available=1", (org,)).fetchone()[0])
        saved_signals = int(c.execute("SELECT COUNT(*) FROM intent_saved_signals WHERE organization_id=?", (org,)).fetchone()[0])
        discoveries = int(c.execute("SELECT COUNT(*) FROM intent_discoveries WHERE organization_id=?", (org,)).fetchone()[0])
        total_opps = int(c.execute("SELECT COUNT(*) FROM intent_opportunities WHERE organization_id=?", (org,)).fetchone()[0])
        from app.icp.service import listing as list_icps_svc
        icp_list = list_icps_svc(c).get("items", [])
        active_icps = [i for i in icp_list if i.get("status") != "Archived"]
        primary_icp = next((i for i in active_icps if i.get("is_primary")), None)
        from app.notifications import center
        notif_data = center.list_notifications(c, page=1, page_size=1)
        return {
            "tool": tool_name,
            "label": READ_TOOLS[tool_name]["label"],
            "as_of": now(),
            "data": {
                "total_signals": total_signals,
                "new_signals": int(ov.get("new_signals") or 0),
                "high_relevance_signals": int(ov.get("high_relevance") or 0),
                "saved_signals": saved_signals,
                "discoveries_total": discoveries,
                "active_monitors": int(ov.get("active_monitors") or 0),
                "opportunities_total": total_opps,
                "icp_count": len(active_icps),
                "primary_icp": {"id": primary_icp["id"], "name": primary_icp["name"]} if primary_icp else None,
                "unread_notifications": int(notif_data.get("unread_count") or 0),
            },
        }

    if tool_name == "search_signals":
        query = str(p.get("query") or "")[:120]
        source = str(p.get("source") or "")[:40]
        status = str(p.get("status") or "")[:30]
        min_score = max(0, min(100, int(p.get("min_score") or 0)))
        limit = max(1, min(15, int(p.get("limit") or 8)))
        sort = str(p.get("sort") or "score")
        if sort not in ("newest", "oldest", "score", "score_asc", "title"):
            sort = "score"
        res = radar.listing(
            c,
            "signals",
            page=1,
            size=limit,
            search=query,
            source=source,
            status=status,
            min_score=min_score,
            sort=sort,
        )
        items = []
        for s in res.get("items", []):
            items.append({
                "id": s["id"],
                "title": s["title"],
                "excerpt": (s.get("excerpt") or "")[:280],
                "source": s.get("source"),
                "source_url": s.get("source_url"),
                "score": s.get("score"),
                "status": s.get("status"),
                "category": s.get("category"),
                "buying_intent": s.get("buying_intent"),
                "icp_fit": s.get("icp_fit"),
                "observed_at": s.get("observed_at"),
                "saved": bool(s.get("saved")),
                "href": f"/intent-radar/signals/{s['id']}",
            })
        return {
            "tool": tool_name,
            "label": READ_TOOLS[tool_name]["label"],
            "as_of": now(),
            "data": {"total": res.get("total", len(items)), "items": items},
        }

    if tool_name == "get_signal_detail":
        signal_id = str(p.get("signal_id") or "")
        if not signal_id:
            raise HTTPException(422, "signal_id is required.")
        s = radar.get(c, "signals", signal_id)
        from app.intent_radar.source_policy import can_run_ai_analysis
        ai_ok, ai_reason = can_run_ai_analysis(s)
        return {
            "tool": tool_name,
            "label": READ_TOOLS[tool_name]["label"],
            "as_of": now(),
            "data": {
                "id": s["id"],
                "title": s["title"],
                "excerpt": (s.get("excerpt") or "")[:900],
                "source": s.get("source"),
                "source_url": s.get("source_url"),
                "score": s.get("score"),
                "status": s.get("status"),
                "category": s.get("category"),
                "buying_intent": s.get("buying_intent"),
                "icp_fit": s.get("icp_fit"),
                "observed_at": s.get("observed_at"),
                "available": bool(s.get("available")),
                "saved": bool(s.get("saved")),
                "opportunity_eligible": bool((s.get("opportunity_eligibility") or {}).get("eligible")),
                "ai_processing_allowed": ai_ok,
                "ai_policy_note": ai_reason,
                "href": f"/intent-radar/signals/{s['id']}",
            },
        }

    if tool_name == "list_discoveries":
        from app.intent_radar import discovery_workspace
        limit = max(1, min(15, int(p.get("limit") or 8)))
        res = discovery_workspace.list_discoveries(c, page=1, page_size=limit, search=str(p.get("query") or "")[:120])
        items = [
            {
                "id": d["id"],
                "title": d.get("title") or "Discovery run",
                "status": d.get("status"),
                "matched_count": d.get("matched_count") or 0,
                "sources": d.get("sources") or [],
                "created_at": d.get("created_at"),
                "href": f"/intent-radar/discover/runs/{d['id']}",
            }
            for d in res.get("items", [])
        ]
        return {
            "tool": tool_name,
            "label": READ_TOOLS[tool_name]["label"],
            "as_of": now(),
            "data": {"total": res.get("total", len(items)), "items": items},
        }

    if tool_name == "list_icps":
        from app.icp.service import listing as list_icps_svc
        res = list_icps_svc(c)
        items = []
        for icp in res.get("items", []):
            comp = (icp.get("criteria") or {}).get("company") or {}
            intent = (icp.get("criteria") or {}).get("intent") or {}
            items.append({
                "id": icp["id"],
                "name": icp["name"],
                "status": icp["status"],
                "is_primary": bool(icp.get("is_primary")),
                "description": (icp.get("description") or "")[:240],
                "industries": comp.get("industries") or [],
                "pain_points": intent.get("pain_points") or [],
                "keywords": intent.get("search_terms") or intent.get("business_needs") or [],
                "competitors": intent.get("competitors") or [],
                "related_counts": icp.get("related_counts") or {},
                "href": "/intent-radar/ideal-customers",
            })
        return {
            "tool": tool_name,
            "label": READ_TOOLS[tool_name]["label"],
            "as_of": now(),
            "data": {"total": len(items), "items": items},
        }

    if tool_name == "compare_icps_with_signals":
        from app.icp.service import compare_profiles
        res = compare_profiles(c)
        return {
            "tool": tool_name,
            "label": READ_TOOLS[tool_name]["label"],
            "as_of": now(),
            "data": res,
        }

    if tool_name == "list_monitors":
        res = radar.listing(c, "monitors", page=1, size=15)
        items = [
            {
                "id": m["id"],
                "name": m["name"],
                "status": m["status"],
                "goal": m.get("goal") or "",
                "keywords": (m.get("configuration") or {}).get("keywords") or [],
                "sources": (m.get("configuration") or {}).get("sources") or [],
                "last_checked": m.get("last_checked"),
                "href": "/intent-radar/monitors",
            }
            for m in res.get("items", [])
        ]
        return {
            "tool": tool_name,
            "label": READ_TOOLS[tool_name]["label"],
            "as_of": now(),
            "data": {"total": res.get("total", len(items)), "items": items},
        }

    if tool_name == "list_opportunities":
        res = radar.listing(c, "opportunities", page=1, size=15)
        items = [
            {
                "id": o["id"],
                "signal_id": o.get("signal_id"),
                "signal_title": (o.get("signal") or {}).get("title") or "Linked signal",
                "status": o["status"],
                "priority": o["priority"],
                "next_action": o.get("next_action") or "",
                "notes": (o.get("notes") or "")[:200],
                "href": "/intent-radar/opportunities",
            }
            for o in res.get("items", [])
        ]
        return {
            "tool": tool_name,
            "label": READ_TOOLS[tool_name]["label"],
            "as_of": now(),
            "data": {"total": res.get("total", len(items)), "items": items},
        }

    if tool_name == "get_sources_health":
        from app.intent_radar import connectors
        from app.intent_radar.youtube_source import policy_state as yt_policy
        sources = connectors.catalog(c)
        feeds_count = 0
        try:
            row = c.execute(
                "SELECT configuration_json FROM intent_source_configs WHERE organization_id=? AND id='custom_feeds'",
                (org,),
            ).fetchone()
            if row and row["configuration_json"]:
                cfg = json.loads(row["configuration_json"])
                feeds_list = cfg.get("items") if isinstance(cfg, dict) else cfg if isinstance(cfg, list) else []
                feeds_count = sum(1 for f in feeds_list if isinstance(f, dict) and f.get("enabled", True))
        except Exception:
            feeds_count = 0
        return {
            "tool": tool_name,
            "label": READ_TOOLS[tool_name]["label"],
            "as_of": now(),
            "data": {
                "sources": [
                    {
                        "id": s["id"],
                        "name": s["name"],
                        "state": s["state"],
                        "selectable": bool(s.get("selectable")),
                        "ai_policy": "Blocked by YouTube policy" if s["id"] == "youtube" and not get_settings().intent_radar_youtube_ai_analytics_enabled else "Per-publisher opt-in required" if s["id"] == "discourse" else "Eligible",
                    }
                    for s in sources
                ],
                "enabled_custom_feeds": feeds_count,
                "youtube_ai_analytics_enabled": bool(yt_policy().get("ai_analytics_enabled")),
            },
        }

    if tool_name == "get_billing_usage":
        from app.billing.overview import overview as billing_overview
        ov = billing_overview(c)
        access = ov.get("access") or {}
        usage = [
            {
                "dimension": u.get("dimension"),
                "label": u.get("label"),
                "used": u.get("used"),
                "limit": u.get("limit"),
                "remaining": u.get("remaining"),
            }
            for u in (ov.get("usage") or [])
        ]
        return {
            "tool": tool_name,
            "label": READ_TOOLS[tool_name]["label"],
            "as_of": now(),
            "data": {
                "plan_name": access.get("plan_name") or access.get("kind") or "Workspace access",
                "access_kind": access.get("kind"),
                "is_trial": bool(access.get("is_trial")),
                "cancel_at_period_end": bool(access.get("cancel_at_period_end")),
                "period_end": access.get("period_end"),
                "usage": usage,
                "href": "/settings?category=billing&tab=overview",
            },
        }

    if tool_name == "list_notifications":
        from app.notifications import center
        res = center.list_notifications(c, page=1, page_size=8)
        return {
            "tool": tool_name,
            "label": READ_TOOLS[tool_name]["label"],
            "as_of": now(),
            "data": {
                "unread_count": res.get("unread_count", 0),
                "items": res.get("items", []),
                "href": "/notifications",
            },
        }

    if tool_name == "search_research_library":
        from app.intent_radar import discovery_workspace
        bookmarks = radar.saved(c, page=1, size=10)
        saved_searches = discovery_workspace.list_saved_searches(c, page=1, page_size=10)
        return {
            "tool": tool_name,
            "label": READ_TOOLS[tool_name]["label"],
            "as_of": now(),
            "data": {
                "bookmarks_total": bookmarks.get("total", 0),
                "bookmarks": [
                    {
                        "signal_id": b["signal_id"],
                        "collection": b.get("collection") or "Inbox",
                        "title": (b.get("signal") or {}).get("title") or "Saved signal",
                        "href": f"/intent-radar/signals/{b['signal_id']}",
                    }
                    for b in bookmarks.get("items", [])
                ],
                "saved_searches_total": saved_searches.get("total", 0),
                "saved_searches": [
                    {
                        "id": ss["id"],
                        "name": ss["name"],
                        "href": "/intent-radar/discover/saved",
                    }
                    for ss in saved_searches.get("items", [])
                ],
            },
        }

    raise HTTPException(400, f"Unsupported read tool: {tool_name}")


# ---------------------------------------------------------------------------
# Authorized Write Tool Execution (Called ONLY After Explicit User Approval)
# ---------------------------------------------------------------------------

def _record_ai_audit(c, org: str, actor: str, tool_name: str, entity: str, result: str, details: dict) -> None:
    c.execute(
        "INSERT INTO audit_log(id,actor,action,entity,result,details_json,organization_id,created_at) VALUES(?,?,?,?,?,?,?,?)",
        (
            str(uuid.uuid4()),
            actor,
            f"AI_AGENT_{tool_name.upper()}",
            entity[:160],
            result,
            json.dumps(details, default=str)[:4000],
            org,
            now(),
        ),
    )


def execute_write_tool(c, tool_name: str, params: dict[str, Any], *, action_id: str) -> dict[str, Any]:
    """Execute a previously proposed write action after explicit user approval."""
    if tool_name not in WRITE_TOOLS:
        raise HTTPException(400, f"Unsupported action tool: {tool_name}")

    ctx = analytics.access(c)
    org = ctx.organization_id
    role = membership_role(c, ctx.actor, org)
    spec = WRITE_TOOLS[tool_name]
    if role not in spec["required_roles"]:
        raise HTTPException(403, f"Your workspace role ({role}) cannot execute {spec['label']}.")

    # Idempotency guard via audit_log action_id check
    existing = c.execute(
        "SELECT details_json FROM audit_log WHERE organization_id=? AND entity=? AND result='SUCCESS' ORDER BY created_at DESC LIMIT 1",
        (org, f"ai-action:{action_id}"),
    ).fetchone()
    if existing and existing["details_json"]:
        try:
            cached = json.loads(existing["details_json"])
            if cached.get("execution_result"):
                return {**cached["execution_result"], "idempotent_replay": True}
        except Exception:
            pass

    result: dict[str, Any]
    launch_job_id: str | None = None

    if tool_name == "create_icp":
        body = CreateIcpParams.model_validate(params)
        from app.icp.models import CompanyCriteria, Criteria, IntentCriteria, Create as IcpCreate
        from app.icp import service as icp_svc

        profile_payload = IcpCreate(
            name=body.name,
            description=body.description or f"Created via PlaneByte AI Assistant for {body.name}",
            status="ACTIVE",
            request_id=uuid.uuid5(uuid.NAMESPACE_URL, f"{org}:ai-icp:{action_id}"),
            criteria=Criteria(
                company=CompanyCriteria(industries=body.industries),
                intent=IntentCriteria(
                    pain_points=body.pain_points,
                    business_needs=body.business_needs,
                    search_terms=body.keywords,
                    competitors=body.competitors,
                    exclusions=body.exclusions,
                ),
            ),
        )
        created = icp_svc.create(c, profile_payload)
        if body.set_as_primary:
            created = icp_svc.set_primary(c, created["id"])
        result = {
            "tool": tool_name,
            "summary": f"Created Ideal Customer Profile '{created['name']}'.",
            "entity_type": "icp",
            "entity_id": created["id"],
            "resource_url": "/intent-radar/ideal-customers",
            "data": {"id": created["id"], "name": created["name"], "is_primary": bool(created.get("is_primary"))},
        }

    elif tool_name == "set_primary_icp":
        body = SetPrimaryIcpParams.model_validate(params)
        from app.icp import service as icp_svc
        updated = icp_svc.set_primary(c, body.icp_id)
        result = {
            "tool": tool_name,
            "summary": f"Set '{updated['name']}' as the primary workspace ICP.",
            "entity_type": "icp",
            "entity_id": updated["id"],
            "resource_url": "/intent-radar/ideal-customers",
            "data": {"id": updated["id"], "name": updated["name"]},
        }

    elif tool_name == "save_search":
        body = SaveSearchParams.model_validate(params)
        from app.intent_radar import discovery_workspace
        allowed = _allowed_sources(c)
        chosen_sources = [s for s in body.sources if s in allowed] or [next(iter(allowed), "hacker_news")]
        saved = discovery_workspace.save_search(
            c,
            discovery_workspace.SavedSearchInput(
                name=body.name,
                description=body.description,
                original_prompt=f"AI Assistant saved search: {', '.join(body.keywords)}",
                configuration=radar_models.Search(
                    sources=chosen_sources,
                    keywords=body.keywords,
                    min_relevance=body.min_relevance,
                ),
            ),
        )
        result = {
            "tool": tool_name,
            "summary": f"Saved search template '{saved['name']}'.",
            "entity_type": "saved_search",
            "entity_id": saved["id"],
            "resource_url": "/intent-radar/discover/saved",
            "data": {"id": saved["id"], "name": saved["name"]},
        }

    elif tool_name == "run_discovery":
        body = RunDiscoveryParams.model_validate(params)
        from app.intent_radar import discovery
        allowed = _allowed_sources(c)
        chosen_sources = [s for s in body.sources if s in allowed] or [next(iter(allowed), "hacker_news")]
        req_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{org}:ai-discovery:{action_id}")
        disc_payload = radar_models.Discovery(
            configuration=radar_models.Search(
                sources=chosen_sources,
                keywords=body.keywords,
                min_relevance=body.min_relevance,
                icp_id=uuid.UUID(body.icp_id) if body.icp_id else None,
            ),
            request_id=req_id,
            title=body.title or f"AI Discovery: {', '.join(body.keywords[:3])}"[:120],
            original_prompt=f"AI Assistant discovery for {', '.join(body.keywords)}",
        )
        job = discovery.create(c, disc_payload)
        launch_job_id = job["id"]
        disc_id = job.get("discovery_id")
        result = {
            "tool": tool_name,
            "summary": f"Started discovery search across {', '.join(chosen_sources)}.",
            "entity_type": "discovery",
            "entity_id": disc_id or job["id"],
            "job_id": job["id"],
            "resource_url": f"/intent-radar/discover/runs/{disc_id}" if disc_id else "/intent-radar/discover/history",
            "data": {"job_id": job["id"], "discovery_id": disc_id, "sources": chosen_sources},
        }

    elif tool_name == "create_monitor":
        body = CreateMonitorParams.model_validate(params)
        allowed = _allowed_sources(c)
        chosen_sources = [s for s in body.sources if s in allowed] or [next(iter(allowed), "hacker_news")]
        req_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{org}:ai-monitor:{action_id}")
        created = radar.save_monitor(
            c,
            radar_models.Monitor(
                name=body.name,
                description=body.description or f"Created via AI Assistant tracking {', '.join(body.keywords[:4])}",
                goal=body.goal,
                status=body.status,
                configuration=radar_models.Search(sources=chosen_sources, keywords=body.keywords),
                request_id=req_id,
            ),
        )
        result = {
            "tool": tool_name,
            "summary": f"Created {created['status'].lower()} monitor '{created['name']}'.",
            "entity_type": "monitor",
            "entity_id": created["id"],
            "resource_url": "/intent-radar/monitors",
            "data": {"id": created["id"], "name": created["name"], "status": created["status"]},
        }

    elif tool_name == "toggle_monitor":
        body = ToggleMonitorParams.model_validate(params)
        old = radar.get(c, "monitors", body.monitor_id)
        updated = radar.save_monitor(
            c,
            radar_models.Monitor(
                name=old["name"],
                description=old.get("description") or "",
                goal=old.get("goal") or "",
                status=body.status,
                configuration=radar_models.Search.model_validate(old["configuration"]),
                revision=old["revision"],
            ),
            body.monitor_id,
        )
        result = {
            "tool": tool_name,
            "summary": f"Updated monitor '{updated['name']}' to {updated['status']}.",
            "entity_type": "monitor",
            "entity_id": updated["id"],
            "resource_url": "/intent-radar/monitors",
            "data": {"id": updated["id"], "name": updated["name"], "status": updated["status"]},
        }

    elif tool_name == "save_signal":
        body = SaveSignalParams.model_validate(params)
        sig = radar.bookmark(c, body.signal_id)
        result = {
            "tool": tool_name,
            "summary": f"Saved '{sig['title'][:80]}' to Research Library.",
            "entity_type": "signal",
            "entity_id": sig["id"],
            "resource_url": f"/intent-radar/signals/{sig['id']}",
            "data": {"id": sig["id"], "title": sig["title"]},
        }

    elif tool_name == "update_signal_status":
        body = UpdateSignalStatusParams.model_validate(params)
        old = radar.get(c, "signals", body.signal_id)
        sig = radar.review(
            c,
            body.signal_id,
            radar_models.Review(status=body.status, notes=body.notes, revision=old["revision"]),
        )
        result = {
            "tool": tool_name,
            "summary": f"Updated signal status to {sig['status']}.",
            "entity_type": "signal",
            "entity_id": sig["id"],
            "resource_url": f"/intent-radar/signals/{sig['id']}",
            "data": {"id": sig["id"], "status": sig["status"]},
        }

    elif tool_name == "create_opportunity":
        body = CreateOpportunityParams.model_validate(params)
        opp = radar.opportunity(
            c,
            body.signal_id,
            create_body=radar_models.OpportunityCreate(
                priority=body.priority,
                notes=body.notes,
                next_action=body.next_action,
            ),
        )
        result = {
            "tool": tool_name,
            "summary": "Linked opportunity created from signal." if not opp.get("already_existed") else "Opportunity already existed for this signal.",
            "entity_type": "opportunity",
            "entity_id": opp["id"],
            "resource_url": "/intent-radar/opportunities",
            "data": {"id": opp["id"], "status": opp["status"], "priority": opp["priority"]},
        }

    elif tool_name == "update_opportunity":
        body = UpdateOpportunityParams.model_validate(params)
        old = radar.get(c, "opportunities", body.opportunity_id)
        opp = radar.opportunity(
            c,
            body.opportunity_id,
            body=radar_models.OpportunityUpdate(
                status=body.status,
                priority=body.priority,
                notes=body.notes,
                next_action=body.next_action,
                revision=old["revision"],
            ),
        )
        result = {
            "tool": tool_name,
            "summary": f"Updated opportunity to {opp['status']} ({opp['priority']} priority).",
            "entity_type": "opportunity",
            "entity_id": opp["id"],
            "resource_url": "/intent-radar/opportunities",
            "data": {"id": opp["id"], "status": opp["status"], "priority": opp["priority"]},
        }

    else:
        raise HTTPException(400, f"Action tool {tool_name} is not implemented.")

    _record_ai_audit(
        c,
        org,
        ctx.actor,
        tool_name,
        f"ai-action:{action_id}",
        "SUCCESS",
        {"action_id": action_id, "tool": tool_name, "params": params, "execution_result": result},
    )
    try:
        from app.notifications import center
        center.emit(
            c,
            org,
            category="ai",
            event_type=f"AI_AGENT_{tool_name.upper()}",
            title=f"AI Assistant completed: {spec['label']}",
            description=result["summary"],
            priority="normal",
            resource_url=result["resource_url"],
            dedupe_key=f"ai-action:{action_id}",
            recipient_email=ctx.actor,
        )
    except Exception:
        pass

    if launch_job_id:
        result["_launch_job_id"] = launch_job_id
    return result


def list_action_history(c, *, limit: int = 30) -> dict[str, Any]:
    ctx = analytics.access(c)
    rows = c.execute(
        "SELECT id,actor,action,entity,result,details_json,created_at FROM audit_log "
        "WHERE organization_id=? AND action LIKE 'AI_AGENT_%' ORDER BY created_at DESC LIMIT ?",
        (ctx.organization_id, max(1, min(100, limit))),
    ).fetchall()
    items = []
    for r in rows:
        details: dict[str, Any] = {}
        try:
            if r["details_json"]:
                details = json.loads(r["details_json"])
        except Exception:
            pass
        exec_res = details.get("execution_result") or {}
        items.append({
            "id": r["id"],
            "actor": r["actor"],
            "action": r["action"],
            "tool": details.get("tool") or r["action"].replace("AI_AGENT_", "").lower(),
            "result": r["result"],
            "summary": exec_res.get("summary") or details.get("summary") or r["action"],
            "resource_url": exec_res.get("resource_url") or "/intelligence/assistant",
            "created_at": r["created_at"],
        })
    return {"items": items}
