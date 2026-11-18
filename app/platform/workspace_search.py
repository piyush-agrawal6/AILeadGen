"""Workspace-scoped Universal Search across authorized Intent Radar, Intelligence, Sources, and Help records."""
from __future__ import annotations

import json
from typing import Any

from app.config.settings import get_settings
from app.platform.product_help import search as search_help


def _rank_score(query_cf: str, title: str, subtitle: str = "", extra: str = "") -> int:
    t = (title or "").casefold()
    s = (subtitle or "").casefold()
    e = (extra or "").casefold()
    if t == query_cf:
        return 100
    if t.startswith(query_cf):
        return 85
    if query_cf in t:
        return 70
    if query_cf in s:
        return 50
    if query_cf in e:
        return 35
    terms = [w for w in query_cf.split() if len(w) >= 2]
    if terms:
        hits = sum(1 for w in terms if w in t or w in s or w in e)
        if hits:
            return 20 + min(45, hits * 15)
    return 0


def _safe_json(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def search_workspace(
    c,
    *,
    organization_id: str | None,
    actor: str,
    query: str,
    category: str = "all",
    limit: int = 6,
) -> dict[str, Any]:
    q = (query or "").strip()[:160]
    q_cf = q.casefold()
    like = f"%{q_cf}%"
    bound = max(1, min(int(limit), 15))
    cat = (category or "all").strip().lower()

    results: dict[str, list[dict[str, Any]]] = {
        "discoveries": [],
        "saved_searches": [],
        "signals": [],
        "opportunities": [],
        "monitors": [],
        "icps": [],
        "company": [],
        "sources": [],
        "intelligence": [],
        "help": [],
    }
    partial_errors: list[str] = []

    # Always allow Help search (even during onboarding / pre-activation)
    if cat in ("all", "help"):
        help_items = search_help(q, limit=bound) if q else search_help("", limit=min(5, bound))
        for item in help_items:
            results["help"].append({
                "id": f"help:{item['id']}",
                "type": "help",
                "title": item["title"],
                "subtitle": item["body"][:140],
                "href": f"/help?article={item['id']}",
                "badge": item.get("category") or "Help",
                "meta": {"target_href": item.get("href")},
                "score": _rank_score(q_cf, item["title"], item["body"]) if q_cf else 40,
            })

    if not organization_id:
        return {"query": q, "organization_id": None, "radar_enabled": False, "growth_enabled": False, "groups": results, "partial_errors": partial_errors}

    # Verify active membership + Intent Radar entitlement server-side
    from app.api.organization import membership_role
    from app.intent_radar.permissions import availability

    role = membership_role(c, actor, organization_id)
    if not role:
        return {"query": q, "organization_id": organization_id, "radar_enabled": False, "growth_enabled": False, "groups": results, "partial_errors": partial_errors}

    avail = availability(c, organization_id)
    radar_enabled = bool(avail.get("enabled"))
    growth_enabled = bool(radar_enabled and get_settings().intent_radar_growth_enabled)

    # ICPs are accessible even during setup/onboarding
    if cat in ("all", "icps", "intelligence"):
        try:
            if q_cf:
                rows = c.execute(
                    """SELECT id, name, description, status, criteria_json, updated_at
                       FROM ideal_customer_profiles
                       WHERE organization_id=? AND status<>'DELETED'
                         AND (LOWER(name) LIKE ? OR LOWER(COALESCE(description,'')) LIKE ? OR LOWER(COALESCE(criteria_json,'')) LIKE ?)
                       ORDER BY updated_at DESC LIMIT ?""",
                    (organization_id, like, like, like, bound),
                ).fetchall()
            else:
                rows = c.execute(
                    """SELECT id, name, description, status, criteria_json, updated_at
                       FROM ideal_customer_profiles
                       WHERE organization_id=? AND status<>'DELETED'
                       ORDER BY updated_at DESC LIMIT ?""",
                    (organization_id, min(4, bound)),
                ).fetchall()
            for r in rows:
                results["icps"].append({
                    "id": f"icp:{r['id']}",
                    "type": "icp",
                    "title": r["name"],
                    "subtitle": (r["description"] or "Ideal Customer Profile")[:140],
                    "href": "/intent-radar/ideal-customers",
                    "badge": r["status"],
                    "updated_at": r["updated_at"],
                    "score": _rank_score(q_cf, r["name"], r["description"] or "", r["criteria_json"] or "") if q_cf else 50,
                })
        except Exception:
            partial_errors.append("icps")

    # Company Profile & Services (accessible even during setup/onboarding)
    if cat in ("all", "company", "intelligence") and q_cf:
        try:
            prof = c.execute(
                """SELECT p.display_name, p.website_url, p.industry, p.short_description, p.long_description,
                          p.country, p.city, p.target_customer_types_json, p.target_industries_json, p.specialties_json,
                          p.updated_at, o.name AS org_name
                   FROM organizations o
                   LEFT JOIN organization_profiles p ON p.organization_id=o.id
                   WHERE o.id=?""",
                (organization_id,),
            ).fetchone()
            if prof:
                cname = prof["display_name"] or prof["org_name"] or "Company Profile"
                extra = " ".join(
                    str(prof[k] or "")
                    for k in ("website_url", "industry", "short_description", "long_description", "country", "city", "target_customer_types_json", "target_industries_json", "specialties_json")
                )
                score = _rank_score(q_cf, cname, prof["industry"] or prof["short_description"] or "", extra)
                if score > 0:
                    results["company"].append({
                        "id": f"company:{organization_id}",
                        "type": "company",
                        "title": cname,
                        "subtitle": (prof["short_description"] or prof["industry"] or prof["website_url"] or "Organization Profile")[:140],
                        "href": "/settings?category=company&tab=profile",
                        "badge": "Company Profile",
                        "updated_at": prof["updated_at"],
                        "score": score,
                    })
            svc_rows = c.execute(
                """SELECT id, name, category, description, updated_at
                   FROM organization_services
                   WHERE organization_id=? AND active=1
                     AND (LOWER(name) LIKE ? OR LOWER(COALESCE(category,'')) LIKE ? OR LOWER(COALESCE(description,'')) LIKE ?)
                   ORDER BY updated_at DESC LIMIT ?""",
                (organization_id, like, like, like, min(3, bound)),
            ).fetchall()
            for sr in svc_rows:
                results["company"].append({
                    "id": f"service:{sr['id']}",
                    "type": "company",
                    "title": sr["name"],
                    "subtitle": (sr["description"] or sr["category"] or "Product / Service")[:140],
                    "href": "/settings?category=company&tab=profile",
                    "badge": sr["category"] or "Offering",
                    "updated_at": sr["updated_at"],
                    "score": _rank_score(q_cf, sr["name"], sr["description"] or "", sr["category"] or ""),
                })
        except Exception:
            partial_errors.append("company")

    if not radar_enabled:
        return {
            "query": q,
            "organization_id": organization_id,
            "radar_enabled": False,
            "growth_enabled": False,
            "groups": results,
            "partial_errors": partial_errors,
        }

    # 1. Discoveries
    if cat in ("all", "discoveries"):
        try:
            if q_cf:
                rows = c.execute(
                    """SELECT d.id, d.created_at, d.configuration_json, m.title, m.original_prompt, m.search_mode
                       FROM intent_discoveries d
                       LEFT JOIN intent_discovery_runs_meta m
                         ON m.organization_id=d.organization_id AND m.discovery_id=d.id
                       WHERE d.organization_id=? AND (m.deleted_at IS NULL)
                         AND (LOWER(COALESCE(m.title,'')) LIKE ? OR LOWER(COALESCE(m.original_prompt,'')) LIKE ? OR LOWER(COALESCE(d.configuration_json,'')) LIKE ?)
                       ORDER BY d.created_at DESC LIMIT ?""",
                    (organization_id, like, like, like, bound),
                ).fetchall()
            else:
                rows = c.execute(
                    """SELECT d.id, d.created_at, d.configuration_json, m.title, m.original_prompt, m.search_mode
                       FROM intent_discoveries d
                       LEFT JOIN intent_discovery_runs_meta m
                         ON m.organization_id=d.organization_id AND m.discovery_id=d.id
                       WHERE d.organization_id=? AND (m.deleted_at IS NULL)
                       ORDER BY d.created_at DESC LIMIT ?""",
                    (organization_id, min(4, bound)),
                ).fetchall()
            for r in rows:
                cfg = _safe_json(r["configuration_json"])
                kws = cfg.get("keywords") or []
                title = r["title"] or r["original_prompt"] or (", ".join(kws[:4]) if kws else "Discovery Run")
                sources = cfg.get("sources") or []
                subtitle = f"{len(sources)} source(s)" + (f" · {', '.join(kws[:3])}" if kws else "")
                results["discoveries"].append({
                    "id": f"discovery:{r['id']}",
                    "type": "discovery",
                    "title": str(title)[:110],
                    "subtitle": subtitle[:140],
                    "href": f"/intent-radar/discover/runs/{r['id']}",
                    "badge": (r["search_mode"] or "discovery").upper(),
                    "updated_at": r["created_at"],
                    "meta": {"sources": sources[:6], "keywords": kws[:6]},
                    "score": _rank_score(q_cf, str(title), subtitle, r["original_prompt"] or "") if q_cf else 55,
                })
        except Exception:
            partial_errors.append("discoveries")

    # 2. Saved Searches
    if cat in ("all", "discoveries"):
        try:
            if q_cf:
                rows = c.execute(
                    """SELECT id, name, description, original_prompt, configuration_json, updated_at
                       FROM intent_saved_searches
                       WHERE organization_id=?
                         AND (LOWER(name) LIKE ? OR LOWER(COALESCE(description,'')) LIKE ? OR LOWER(COALESCE(original_prompt,'')) LIKE ? OR LOWER(COALESCE(configuration_json,'')) LIKE ?)
                       ORDER BY updated_at DESC LIMIT ?""",
                    (organization_id, like, like, like, like, bound),
                ).fetchall()
            else:
                rows = c.execute(
                    """SELECT id, name, description, original_prompt, configuration_json, updated_at
                       FROM intent_saved_searches
                       WHERE organization_id=?
                       ORDER BY updated_at DESC LIMIT ?""",
                    (organization_id, min(3, bound)),
                ).fetchall()
            for r in rows:
                cfg = _safe_json(r["configuration_json"])
                results["saved_searches"].append({
                    "id": f"saved_search:{r['id']}",
                    "type": "saved_search",
                    "title": r["name"],
                    "subtitle": (r["description"] or r["original_prompt"] or "Saved search configuration")[:140],
                    "href": "/intent-radar/discover/saved",
                    "badge": "Saved Search",
                    "updated_at": r["updated_at"],
                    "meta": {"sources": (cfg.get("sources") or [])[:6]},
                    "score": _rank_score(q_cf, r["name"], r["description"] or "", r["original_prompt"] or "") if q_cf else 45,
                })
        except Exception:
            partial_errors.append("saved_searches")

    # 3. Intent Signals (strictly enforcing available=1 AND retention_sql)
    if cat in ("all", "discoveries", "signals"):
        try:
            from app.intent_radar import service as radar_service
            prefs = radar_service.preferences(c)
            ret_sql, ret_args = radar_service.retention_sql(c, int(prefs.get("source_retention_days", 30)))
            if q_cf:
                rows = c.execute(
                    f"""SELECT id, title, excerpt, source, category, score, status, observed_at
                        FROM intent_signals
                        WHERE organization_id=? AND available=1 AND {ret_sql}
                          AND (LOWER(title) LIKE ? OR LOWER(COALESCE(excerpt,'')) LIKE ? OR LOWER(source) LIKE ? OR LOWER(COALESCE(category,'')) LIKE ?)
                        ORDER BY score DESC, observed_at DESC LIMIT ?""",
                    (organization_id, *ret_args, like, like, like, like, bound),
                ).fetchall()
            else:
                rows = c.execute(
                    f"""SELECT id, title, excerpt, source, category, score, status, observed_at
                        FROM intent_signals
                        WHERE organization_id=? AND available=1 AND {ret_sql}
                        ORDER BY score DESC, observed_at DESC LIMIT ?""",
                    (organization_id, *ret_args, min(4, bound)),
                ).fetchall()
            for r in rows:
                results["signals"].append({
                    "id": f"signal:{r['id']}",
                    "type": "signal",
                    "title": (r["title"] or "Intent Signal")[:110],
                    "subtitle": (r["excerpt"] or "")[:150],
                    "href": f"/intent-radar/signals/{r['id']}",
                    "badge": f"{r['source']} · {r['score']}",
                    "updated_at": r["observed_at"],
                    "meta": {"source": r["source"], "score": r["score"], "status": r["status"], "category": r["category"]},
                    "score": _rank_score(q_cf, r["title"] or "", r["excerpt"] or "", r["source"] or "") if q_cf else int(r["score"] or 50),
                })
        except Exception:
            partial_errors.append("signals")

    # 4. Opportunities (joined with intent_signals)
    if cat in ("all", "monitors", "opportunities"):
        try:
            if q_cf:
                rows = c.execute(
                    """SELECT o.id, o.status, o.priority, o.notes, o.next_action, o.updated_at,
                              CASE WHEN s.available=1 THEN s.title ELSE 'Opportunity' END AS signal_title,
                              s.source AS signal_source
                       FROM intent_opportunities o
                       LEFT JOIN intent_signals s ON s.organization_id=o.organization_id AND s.id=o.signal_id
                       WHERE o.organization_id=?
                         AND (LOWER(COALESCE(o.notes,'')) LIKE ? OR LOWER(COALESCE(o.next_action,'')) LIKE ? OR LOWER(o.status) LIKE ? OR (s.available=1 AND LOWER(COALESCE(s.title,'')) LIKE ?))
                       ORDER BY o.updated_at DESC LIMIT ?""",
                    (organization_id, like, like, like, like, bound),
                ).fetchall()
            else:
                rows = c.execute(
                    """SELECT o.id, o.status, o.priority, o.notes, o.next_action, o.updated_at,
                              CASE WHEN s.available=1 THEN s.title ELSE 'Opportunity' END AS signal_title,
                              s.source AS signal_source
                       FROM intent_opportunities o
                       LEFT JOIN intent_signals s ON s.organization_id=o.organization_id AND s.id=o.signal_id
                       WHERE o.organization_id=?
                       ORDER BY o.updated_at DESC LIMIT ?""",
                    (organization_id, min(3, bound)),
                ).fetchall()
            for r in rows:
                title = r["signal_title"] or r["next_action"] or "Opportunity"
                subtitle = r["next_action"] or r["notes"] or f"{r['priority']} priority · {r['status']}"
                results["opportunities"].append({
                    "id": f"opportunity:{r['id']}",
                    "type": "opportunity",
                    "title": str(title)[:110],
                    "subtitle": str(subtitle)[:140],
                    "href": f"/intent-radar/opportunities/{r['id']}",
                    "badge": f"{r['priority']} · {r['status']}",
                    "updated_at": r["updated_at"],
                    "meta": {"priority": r["priority"], "status": r["status"], "source": r["signal_source"]},
                    "score": _rank_score(q_cf, str(title), str(subtitle)) if q_cf else 45,
                })
        except Exception:
            partial_errors.append("opportunities")

    # 5. Monitors
    if cat in ("all", "monitors"):
        try:
            if q_cf:
                rows = c.execute(
                    """SELECT id, name, description, goal, status, configuration_json, last_checked, updated_at
                       FROM intent_monitors
                       WHERE organization_id=? AND status<>'Archived'
                         AND (LOWER(name) LIKE ? OR LOWER(COALESCE(description,'')) LIKE ? OR LOWER(COALESCE(goal,'')) LIKE ? OR LOWER(COALESCE(configuration_json,'')) LIKE ?)
                       ORDER BY updated_at DESC LIMIT ?""",
                    (organization_id, like, like, like, like, bound),
                ).fetchall()
            else:
                rows = c.execute(
                    """SELECT id, name, description, goal, status, configuration_json, last_checked, updated_at
                       FROM intent_monitors
                       WHERE organization_id=? AND status<>'Archived'
                       ORDER BY updated_at DESC LIMIT ?""",
                    (organization_id, min(4, bound)),
                ).fetchall()
            for r in rows:
                cfg = _safe_json(r["configuration_json"])
                results["monitors"].append({
                    "id": f"monitor:{r['id']}",
                    "type": "monitor",
                    "title": r["name"],
                    "subtitle": (r["description"] or r["goal"] or ", ".join((cfg.get("keywords") or [])[:4]) or "Monitor")[:140],
                    "href": f"/intent-radar/monitors/{r['id']}",
                    "badge": r["status"],
                    "updated_at": r["last_checked"] or r["updated_at"],
                    "meta": {"status": r["status"], "sources": (cfg.get("sources") or [])[:5]},
                    "score": _rank_score(q_cf, r["name"], r["description"] or "", r["configuration_json"] or "") if q_cf else 50,
                })
        except Exception:
            partial_errors.append("monitors")

    # 6. Research Sources & Custom Feeds
    if cat in ("all", "sources"):
        try:
            from app.intent_radar import connectors
            for src in connectors.catalog(c):
                s_title = src.get("name") or src.get("id") or ""
                s_cov = src.get("coverage") or ""
                s_state = src.get("state") or "Available"
                score = _rank_score(q_cf, s_title, s_cov, src.get("id") or "") if q_cf else 35
                if not q_cf or score > 0:
                    results["sources"].append({
                        "id": f"source:{src.get('id')}",
                        "type": "source",
                        "title": s_title,
                        "subtitle": s_cov[:130],
                        "href": "/settings?category=integrations&tab=sources",
                        "badge": s_state,
                        "meta": {"state": s_state, "source_id": src.get("id")},
                        "score": score,
                    })
            for cfg in connectors.configurations(c):
                f_name = cfg.get("name") or ""
                f_end = cfg.get("endpoint") or ""
                f_fam = cfg.get("family") or "feed"
                score = _rank_score(q_cf, f_name, f_end, f_fam) if q_cf else 30
                if not q_cf or score > 0:
                    results["sources"].append({
                        "id": f"feed:{cfg.get('id')}",
                        "type": "feed",
                        "title": f_name,
                        "subtitle": f"{f_fam.upper()} · {f_end}"[:130],
                        "href": "/settings?category=integrations&tab=feeds",
                        "badge": "Enabled" if cfg.get("enabled") else "Disabled",
                        "meta": {"family": f_fam, "enabled": bool(cfg.get("enabled"))},
                        "score": score,
                    })
            results["sources"].sort(key=lambda x: x["score"], reverse=True)
            results["sources"] = results["sources"][:bound]
        except Exception:
            partial_errors.append("sources")

    # 7. Intelligence (Growth Research/Reports/Themes/Competitors + Research Library)
    if cat in ("all", "intelligence"):
        try:
            if q_cf:
                saved_rows = c.execute(
                    """SELECT b.signal_id, b.collection, b.notes, b.saved_at,
                              CASE WHEN s.available=1 THEN s.title ELSE 'Saved item' END AS signal_title
                       FROM intent_saved_signals b
                       LEFT JOIN intent_signals s ON s.organization_id=b.organization_id AND s.id=b.signal_id
                       WHERE b.organization_id=?
                         AND (LOWER(COALESCE(b.notes,'')) LIKE ? OR LOWER(COALESCE(b.collection,'')) LIKE ? OR (s.available=1 AND LOWER(COALESCE(s.title,'')) LIKE ?))
                       ORDER BY b.saved_at DESC LIMIT ?""",
                    (organization_id, like, like, like, min(4, bound)),
                ).fetchall()
                for r in saved_rows:
                    results["intelligence"].append({
                        "id": f"saved_signal:{r['signal_id']}",
                        "type": "library",
                        "title": (r["signal_title"] or "Saved Signal")[:110],
                        "subtitle": (r["notes"] or f"Collection: {r['collection'] or 'General'}")[:130],
                        "href": f"/intent-radar/signals/{r['signal_id']}",
                        "badge": "Research Library",
                        "updated_at": r["saved_at"],
                        "score": _rank_score(q_cf, r["signal_title"] or "", r["notes"] or "", r["collection"] or ""),
                    })
            if growth_enabled:
                from app.intent_radar.assistant import thread_expression
                t_expr = thread_expression(c)
                if q_cf:
                    g_rows = c.execute(
                        f"""SELECT id, kind, title, question, status, updated_at
                            FROM growth_research
                            WHERE organization_id=? AND ({t_expr} IS NULL)
                              AND (LOWER(COALESCE(title,'')) LIKE ? OR LOWER(COALESCE(question,'')) LIKE ?)
                            ORDER BY updated_at DESC LIMIT ?""",
                        (organization_id, like, like, min(4, bound)),
                    ).fetchall()
                else:
                    g_rows = c.execute(
                        f"""SELECT id, kind, title, question, status, updated_at
                            FROM growth_research
                            WHERE organization_id=? AND ({t_expr} IS NULL)
                            ORDER BY updated_at DESC LIMIT ?""",
                        (organization_id, min(3, bound)),
                    ).fetchall()
                for r in g_rows:
                    href = "/intent-radar/growth/reports" if r["kind"] == "REPORT" else f"/intent-radar/growth/research/{r['id']}"
                    title = r["title"] or r["question"] or r["kind"]
                    results["intelligence"].append({
                        "id": f"growth:{r['id']}",
                        "type": "report" if r["kind"] == "REPORT" else "research",
                        "title": str(title)[:110],
                        "subtitle": (r["question"] or f"Growth {r['kind'].title()}")[:140],
                        "href": href,
                        "badge": r["kind"].title(),
                        "updated_at": r["updated_at"],
                        "score": _rank_score(q_cf, str(title), r["question"] or "") if q_cf else 42,
                    })
                if q_cf:
                    c_rows = c.execute(
                        """SELECT id, name, context, updated_at
                           FROM growth_competitors
                           WHERE organization_id=? AND archived_at IS NULL
                             AND (LOWER(name) LIKE ? OR LOWER(COALESCE(context,'')) LIKE ? OR LOWER(COALESCE(aliases_json,'')) LIKE ?)
                           ORDER BY updated_at DESC LIMIT ?""",
                        (organization_id, like, like, like, min(3, bound)),
                    ).fetchall()
                    for r in c_rows:
                        results["intelligence"].append({
                            "id": f"competitor:{r['id']}",
                            "type": "competitor",
                            "title": r["name"],
                            "subtitle": (r["context"] or "Tracked competitor")[:130],
                            "href": "/intent-radar/growth/competitors",
                            "badge": "Competitor",
                            "updated_at": r["updated_at"],
                            "score": _rank_score(q_cf, r["name"], r["context"] or ""),
                        })
            results["intelligence"].sort(key=lambda x: x["score"], reverse=True)
            results["intelligence"] = results["intelligence"][:bound]
        except Exception:
            partial_errors.append("intelligence")

    # Flatten top results across all groups when query is non-empty
    top: list[dict[str, Any]] = []
    if q_cf:
        for grp_items in results.values():
            top.extend(grp_items)
        top.sort(key=lambda x: x.get("score", 0), reverse=True)
        top = top[:6]

    return {
        "query": q,
        "organization_id": organization_id,
        "radar_enabled": radar_enabled,
        "growth_enabled": growth_enabled,
        "top": top,
        "groups": results,
        "partial_errors": partial_errors,
    }
