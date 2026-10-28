import json
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from app.database.models import (
    Business,
    WebsiteProfile,
    Contact,
    LighthouseResult,
    Finding,
    LeadScore,
    PipelineRun,
    PipelineRunEvent,
    ProcessingStatus,
)


class BusinessRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def insert(self, b: Business) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO businesses (
                run_id, external_overture_id, external_osm_id, name, normalized_name,
                vertical, subcategory, country, country_code, state, city, postcode, address,
                latitude, longitude, phone, normalized_phone, website, domain,
                public_email, instagram, facebook, linkedin, x_url,
                source_overture, source_osm, source_confidence, operating_status,
                is_chain, is_duplicate, is_rejected, rejection_reason, processing_status,
                source_category, source_tags_json, vertical_validation_status,
                vertical_validation_reason, vertical_validation_confidence,
                chain_reason, chain_confidence, website_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                getattr(b, "run_id", None),
                b.external_overture_id, b.external_osm_id, b.name, b.normalized_name,
                b.vertical, b.subcategory, b.country, b.country_code, b.state, b.city, b.postcode, b.address,
                b.latitude, b.longitude, b.phone, b.normalized_phone, b.website, b.domain,
                b.public_email, b.instagram, b.facebook, b.linkedin, b.x_url,
                1 if b.source_overture else 0, 1 if b.source_osm else 0, b.source_confidence, b.operating_status,
                1 if b.is_chain else 0, 1 if b.is_duplicate else 0, 1 if b.is_rejected else 0,
                b.rejection_reason, b.processing_status,
                getattr(b, "source_category", None), getattr(b, "source_tags", None),
                getattr(b, "vertical_validation_status", "VALID"),
                getattr(b, "vertical_validation_reason", None),
                getattr(b, "vertical_validation_confidence", 1.0),
                getattr(b, "chain_reason", None), getattr(b, "chain_confidence", 0.0),
                getattr(b, "website_status", None),
            ),
        )
        b.id = cur.lastrowid
        return b.id

    def bulk_insert(self, businesses: List[Business]) -> List[int]:
        ids = []
        for b in businesses:
            ids.append(self.insert(b))
        return ids

    def update(self, b: Business) -> None:
        self.conn.execute(
            """
            UPDATE businesses SET
                run_id = ?, external_overture_id = ?, external_osm_id = ?, name = ?, normalized_name = ?,
                vertical = ?, subcategory = ?, country = ?, country_code = ?, state = ?, city = ?, postcode = ?, address = ?,
                latitude = ?, longitude = ?, phone = ?, normalized_phone = ?, website = ?, domain = ?,
                public_email = ?, instagram = ?, facebook = ?, linkedin = ?, x_url = ?,
                source_overture = ?, source_osm = ?, source_confidence = ?, operating_status = ?,
                is_chain = ?, is_duplicate = ?, is_rejected = ?, rejection_reason = ?, processing_status = ?,
                source_category = ?, source_tags_json = ?, vertical_validation_status = ?,
                vertical_validation_reason = ?, vertical_validation_confidence = ?,
                chain_reason = ?, chain_confidence = ?, website_status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                getattr(b, "run_id", None),
                b.external_overture_id, b.external_osm_id, b.name, b.normalized_name,
                b.vertical, b.subcategory, b.country, b.country_code, b.state, b.city, b.postcode, b.address,
                b.latitude, b.longitude, b.phone, b.normalized_phone, b.website, b.domain,
                b.public_email, b.instagram, b.facebook, b.linkedin, b.x_url,
                1 if b.source_overture else 0, 1 if b.source_osm else 0, b.source_confidence, b.operating_status,
                1 if b.is_chain else 0, 1 if b.is_duplicate else 0, 1 if b.is_rejected else 0,
                b.rejection_reason, b.processing_status,
                getattr(b, "source_category", None), getattr(b, "source_tags", None),
                getattr(b, "vertical_validation_status", "VALID"),
                getattr(b, "vertical_validation_reason", None),
                getattr(b, "vertical_validation_confidence", 1.0),
                getattr(b, "chain_reason", None), getattr(b, "chain_confidence", 0.0),
                getattr(b, "website_status", None),
                b.id,
            ),
        )

    def get_by_id(self, business_id: int) -> Optional[Business]:
        cur = self.conn.execute("SELECT * FROM businesses WHERE id = ?;", (business_id,))
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_business(row)

    def find_all_candidates(self) -> List[Business]:
        """Return non-rejected, non-duplicate businesses."""
        cur = self.conn.execute(
            "SELECT * FROM businesses WHERE is_rejected = 0 AND is_duplicate = 0 ORDER BY id ASC;"
        )
        return [self._row_to_business(r) for r in cur.fetchall()]

    def list_all(self) -> List[Business]:
        cur = self.conn.execute("SELECT * FROM businesses ORDER BY id ASC;")
        return [self._row_to_business(r) for r in cur.fetchall()]

    def list_by_status(self, status: str) -> List[Business]:
        cur = self.conn.execute("SELECT * FROM businesses WHERE processing_status = ? ORDER BY id ASC;", (status,))
        return [self._row_to_business(r) for r in cur.fetchall()]

    def count(self) -> int:
        cur = self.conn.execute("SELECT COUNT(*) FROM businesses;")
        return cur.fetchone()[0]

    def _row_to_business(self, r: sqlite3.Row) -> Business:
        keys = r.keys()
        return Business(
            id=r["id"],
            run_id=r["run_id"] if "run_id" in keys else None,
            external_overture_id=r["external_overture_id"],
            external_osm_id=r["external_osm_id"],
            name=r["name"],
            normalized_name=r["normalized_name"],
            vertical=r["vertical"],
            subcategory=r["subcategory"],
            country=r["country"],
            country_code=r["country_code"],
            state=r["state"],
            city=r["city"],
            postcode=r["postcode"],
            address=r["address"],
            latitude=r["latitude"],
            longitude=r["longitude"],
            phone=r["phone"],
            normalized_phone=r["normalized_phone"],
            website=r["website"],
            domain=r["domain"],
            public_email=r["public_email"],
            instagram=r["instagram"],
            facebook=r["facebook"],
            linkedin=r["linkedin"],
            x_url=r["x_url"],
            source_overture=bool(r["source_overture"]),
            source_osm=bool(r["source_osm"]),
            source_confidence=r["source_confidence"],
            operating_status=r["operating_status"],
            source_category=r["source_category"] if "source_category" in keys else None,
            source_tags=r["source_tags_json"] if "source_tags_json" in keys else None,
            vertical_validation_status=r["vertical_validation_status"] if "vertical_validation_status" in keys and r["vertical_validation_status"] else "VALID",
            vertical_validation_reason=r["vertical_validation_reason"] if "vertical_validation_reason" in keys else None,
            vertical_validation_confidence=r["vertical_validation_confidence"] if "vertical_validation_confidence" in keys and r["vertical_validation_confidence"] is not None else 1.0,
            is_chain=bool(r["is_chain"]),
            chain_reason=r["chain_reason"] if "chain_reason" in keys else None,
            chain_confidence=r["chain_confidence"] if "chain_confidence" in keys and r["chain_confidence"] is not None else 0.0,
            website_status=r["website_status"] if "website_status" in keys else None,
            is_duplicate=bool(r["is_duplicate"]),
            is_rejected=bool(r["is_rejected"]),
            rejection_reason=r["rejection_reason"],
            processing_status=r["processing_status"],
            created_at=str(r["created_at"]) if r["created_at"] else None,
            updated_at=str(r["updated_at"]) if r["updated_at"] else None,
        )

    def search_leads(
        self,
        search: Optional[str] = None,
        tier: Optional[str] = None,
        min_score: Optional[float] = None,
        vertical: Optional[str] = None,
        country: Optional[str] = None,
        state: Optional[str] = None,
        city: Optional[str] = None,
        website_status: Optional[str] = None,
        has_email: Optional[bool] = None,
        has_phone: Optional[bool] = None,
        has_form: Optional[bool] = None,
        recommended_service: Optional[str] = None,
        min_perf: Optional[float] = None,
        max_perf: Optional[float] = None,
        min_seo: Optional[float] = None,
        max_seo: Optional[float] = None,
        source: Optional[str] = None,
        quality_status: Optional[str] = None,
        run_id: Optional[int] = None,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "score",
        sort_dir: str = "desc",
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Search and paginate leads with comprehensive filtering and joined score/profile metrics."""
        conditions: List[str] = []
        params: List[Any] = []

        if run_id is not None:
            conditions.append("b.run_id = ?")
            params.append(run_id)

        if search:
            s_wild = f"%{search.strip()}%"
            conditions.append("(b.name LIKE ? OR b.city LIKE ? OR b.domain LIKE ?)")
            params.extend([s_wild, s_wild, s_wild])

        if tier:
            conditions.append("s.tier = ?")
            params.append(tier.upper())

        if min_score is not None:
            conditions.append("s.total_score >= ?")
            params.append(min_score)

        if vertical:
            conditions.append("b.vertical = ?")
            params.append(vertical.lower())

        if country:
            conditions.append("b.country LIKE ?")
            params.append(f"%{country}%")

        if state:
            conditions.append("b.state LIKE ?")
            params.append(f"%{state}%")

        if city:
            conditions.append("b.city LIKE ?")
            params.append(f"%{city}%")

        if website_status:
            ws_up = website_status.upper()
            if ws_up == "NO_WEBSITE":
                conditions.append("(b.website IS NULL OR b.website = '' OR b.website_status = 'NO_WEBSITE')")
            elif ws_up == "REACHABLE":
                conditions.append("p.reachable = 1")
            elif ws_up == "UNREACHABLE":
                conditions.append("(b.website IS NOT NULL AND b.website != '' AND (p.reachable IS NULL OR p.reachable = 0))")

        if has_email is True:
            conditions.append("(b.public_email IS NOT NULL AND b.public_email != '' AND b.public_email != 'nan')")
        elif has_email is False:
            conditions.append("(b.public_email IS NULL OR b.public_email = '' OR b.public_email = 'nan')")

        if has_phone is True:
            conditions.append("((b.phone IS NOT NULL AND b.phone != '' AND b.phone != 'nan') OR (b.normalized_phone IS NOT NULL AND b.normalized_phone != ''))")

        if has_form is True:
            conditions.append("(p.contact_page_url IS NOT NULL AND p.contact_page_url != '')")

        if recommended_service:
            conditions.append("s.recommended_service LIKE ?")
            params.append(f"%{recommended_service}%")

        if min_perf is not None:
            conditions.append("lh.performance_score >= ?")
            params.append(min_perf)
        if max_perf is not None:
            conditions.append("lh.performance_score <= ?")
            params.append(max_perf)

        if min_seo is not None:
            conditions.append("lh.seo_score >= ?")
            params.append(min_seo)
        if max_seo is not None:
            conditions.append("lh.seo_score <= ?")
            params.append(max_seo)

        if source:
            s_low = source.lower()
            if s_low == "overture":
                conditions.append("b.source_overture = 1")
            elif s_low == "osm":
                conditions.append("b.source_osm = 1")

        if quality_status:
            qs_up = quality_status.upper()
            if qs_up == "QUALIFIED":
                conditions.append("b.processing_status = 'QUALIFIED'")
            elif qs_up == "REJECTED":
                conditions.append("b.is_rejected = 1")
            elif qs_up == "UNCERTAIN":
                conditions.append("b.vertical_validation_status = 'UNCERTAIN'")
            elif qs_up == "ALL":
                pass
        else:
            # Default to candidates only unless rejected is requested
            conditions.append("b.is_rejected = 0")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # Count total
        count_sql = f"""
            SELECT COUNT(*) FROM businesses b
            LEFT JOIN lead_scores s ON b.id = s.business_id
            LEFT JOIN website_profiles p ON b.id = p.business_id
            LEFT JOIN lighthouse_results lh ON b.id = lh.business_id
            {where_clause}
        """
        total_count = self.conn.execute(count_sql, params).fetchone()[0]

        # Sorting
        sort_map = {
            "score": "COALESCE(s.total_score, 0)",
            "performance": "COALESCE(lh.performance_score, 0)",
            "seo": "COALESCE(lh.seo_score, 0)",
            "name": "b.name",
            "newest": "b.id",
            "oldest": "b.id",
        }
        order_col = sort_map.get(sort_by.lower(), "COALESCE(s.total_score, 0)")
        direction = "ASC" if sort_dir.lower() == "asc" or sort_by.lower() == "oldest" else "DESC"

        limit = max(page_size, 1)
        offset = max((page - 1) * limit, 0)

        query_sql = f"""
            SELECT
                b.id, b.name, b.vertical, b.subcategory, b.country, b.state, b.city,
                b.website, b.domain, b.public_email, b.phone, b.normalized_phone,
                b.instagram, b.facebook, b.linkedin, b.x_url,
                b.source_overture, b.source_osm, b.source_confidence,
                b.vertical_validation_status, b.vertical_validation_reason,
                b.is_chain, b.is_rejected, b.rejection_reason, b.processing_status,
                s.total_score, s.tier, s.website_score, s.seo_opportunity_score,
                s.vertical_opportunity_score, s.contactability_score,
                s.recommended_service, s.recommended_angle, s.calculated_at,
                p.reachable, p.http_status, p.https_enabled, p.contact_page_url,
                p.detected_technologies_json, p.schema_types,
                lh.performance_score, lh.seo_score, lh.accessibility_score, lh.best_practices_score
            FROM businesses b
            LEFT JOIN lead_scores s ON b.id = s.business_id
            LEFT JOIN website_profiles p ON b.id = p.business_id
            LEFT JOIN lighthouse_results lh ON b.id = lh.business_id
            {where_clause}
            ORDER BY {order_col} {direction}, b.id ASC
            LIMIT ? OFFSET ?
        """
        cur = self.conn.execute(query_sql, params + [limit, offset])
        rows = cur.fetchall()

        leads: List[Dict[str, Any]] = []
        for r in rows:
            # Derived web status
            if not r["website"]:
                web_stat = "NO_WEBSITE"
            elif r["reachable"] == 1:
                web_stat = "REACHABLE"
            else:
                web_stat = "UNREACHABLE"

            techs = []
            if r["detected_technologies_json"]:
                try:
                    techs = json.loads(r["detected_technologies_json"])
                except Exception:
                    techs = []

            leads.append({
                "id": r["id"],
                "name": r["name"],
                "vertical": r["vertical"],
                "subcategory": r["subcategory"],
                "location": ", ".join(filter(None, [r["city"], r["state"], r["country"]])),
                "city": r["city"],
                "state": r["state"],
                "country": r["country"],
                "website": r["website"],
                "domain": r["domain"],
                "website_status": web_stat,
                "email": r["public_email"] if r["public_email"] and r["public_email"] != "nan" else None,
                "phone": r["normalized_phone"] or (r["phone"] if r["phone"] != "nan" else None),
                "instagram": r["instagram"],
                "facebook": r["facebook"],
                "linkedin": r["linkedin"],
                "x_url": r["x_url"],
                "score": float(r["total_score"]) if r["total_score"] is not None else 0.0,
                "tier": r["tier"] or "D",
                "recommended_service": r["recommended_service"] or "NONE",
                "recommended_angle": r["recommended_angle"] or "",
                "performance": float(r["performance_score"]) if r["performance_score"] is not None else None,
                "seo": float(r["seo_score"]) if r["seo_score"] is not None else None,
                "accessibility": float(r["accessibility_score"]) if r["accessibility_score"] is not None else None,
                "best_practices": float(r["best_practices_score"]) if r["best_practices_score"] is not None else None,
                "technologies": techs,
                "source": "Overture + OSM" if (r["source_overture"] and r["source_osm"]) else ("Overture" if r["source_overture"] else "OSM"),
                "confidence": float(r["source_confidence"] or 0.5),
                "vertical_validation_status": r["vertical_validation_status"] or "VALID",
                "is_chain": bool(r["is_chain"]),
                "is_rejected": bool(r["is_rejected"]),
                "rejection_reason": r["rejection_reason"],
                "processing_status": r["processing_status"],
                "audit_date": r["calculated_at"],
            })

        return leads, total_count

    def get_lead_detail(self, business_id: int) -> Optional[Dict[str, Any]]:
        """Fetch comprehensive prospect intelligence for a single lead."""
        b = self.get_by_id(business_id)
        if not b:
            return None

        # Fetch joined records
        cur = self.conn.execute("SELECT * FROM lead_scores WHERE business_id = ?;", (business_id,))
        score_row = cur.fetchone()

        cur = self.conn.execute("SELECT * FROM website_profiles WHERE business_id = ?;", (business_id,))
        profile_row = cur.fetchone()

        cur = self.conn.execute("SELECT * FROM lighthouse_results WHERE business_id = ?;", (business_id,))
        lh_row = cur.fetchone()

        cur = self.conn.execute("SELECT * FROM findings WHERE business_id = ? ORDER BY score_points DESC;", (business_id,))
        finding_rows = cur.fetchall()

        cur = self.conn.execute("SELECT * FROM contacts WHERE business_id = ?;", (business_id,))
        contact_rows = cur.fetchall()

        # Score parsing
        score_breakdown = {}
        if score_row and score_row["score_breakdown_json"]:
            try:
                score_breakdown = json.loads(score_row["score_breakdown_json"])
            except Exception:
                score_breakdown = {}

        # Profile parsing
        techs = []
        schemas = []
        if profile_row:
            if profile_row["detected_technologies_json"]:
                try:
                    techs = json.loads(profile_row["detected_technologies_json"])
                except Exception:
                    techs = []
            if profile_row["schema_types"]:
                schemas = [s.strip() for s in profile_row["schema_types"].split(",") if s.strip()]

        findings = [
            {
                "id": f["id"],
                "finding_code": f["finding_code"],
                "category": f["category"],
                "severity": f["severity"],
                "title": f["title"],
                "description": f["description"],
                "evidence": f["evidence"],
                "score_points": f["score_points"],
            }
            for f in finding_rows
        ]

        contacts = [
            {
                "id": c["id"],
                "type": c["contact_type"],
                "value": c["contact_value"],
                "source_type": c["source_type"],
                "confidence": c["confidence"],
            }
            for c in contact_rows
        ]

        web_status = "NO_WEBSITE" if not b.website else ("REACHABLE" if (profile_row and profile_row["reachable"]) else "UNREACHABLE")

        return {
            "business": b.model_dump(),
            "website_status": web_status,
            "score": {
                "total": score_row["total_score"] if score_row else 0.0,
                "tier": score_row["tier"] if score_row else "D",
                "website_score": score_row["website_score"] if score_row else 0.0,
                "seo_score": score_row["seo_opportunity_score"] if score_row else 0.0,
                "vertical_score": score_row["vertical_opportunity_score"] if score_row else 0.0,
                "contactability_score": score_row["contactability_score"] if score_row else 0.0,
                "recommended_service": score_row["recommended_service"] if score_row else "NONE",
                "recommended_angle": score_row["recommended_angle"] if score_row else "",
                "breakdown": score_breakdown,
                "calculated_at": score_row["calculated_at"] if score_row else None,
            } if score_row else None,
            "profile": {
                "http_status": profile_row["http_status"],
                "https_enabled": bool(profile_row["https_enabled"]),
                "reachable": bool(profile_row["reachable"]),
                "final_url": profile_row["final_url"],
                "title": profile_row["html_title"],
                "meta_description": profile_row["meta_description"],
                "has_viewport": bool(profile_row["has_viewport"]),
                "has_h1": bool(profile_row["has_h1"]),
                "has_contact_page": bool(profile_row["has_contact_page"]),
                "contact_page_url": profile_row["contact_page_url"],
                "has_booking": bool(profile_row["has_booking"]),
                "booking_url": profile_row["booking_url"],
                "has_menu": bool(profile_row["has_menu"]),
                "menu_url": profile_row["menu_url"],
                "menu_is_pdf": bool(profile_row["menu_is_pdf"]),
                "technologies": techs,
                "schema_types": schemas,
                "page_count_crawled": profile_row["page_count_crawled"],
                "crawl_duration_ms": profile_row["crawl_duration_ms"],
            } if profile_row else None,
            "lighthouse": {
                "performance": lh_row["performance_score"],
                "seo": lh_row["seo_score"],
                "accessibility": lh_row["accessibility_score"],
                "best_practices": lh_row["best_practices_score"],
                "lcp_ms": lh_row["lcp_ms"],
                "cls": lh_row["cls"],
                "tbt_ms": lh_row["tbt_ms"],
                "fcp_ms": lh_row["fcp_ms"],
                "speed_index_ms": lh_row["speed_index_ms"],
            } if lh_row else None,
            "findings": findings,
            "contacts": contacts,
        }

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """Aggregate high-level prospecting and pipeline metrics for dashboard overview."""
        total_biz = self.conn.execute("SELECT COUNT(*) FROM businesses;").fetchone()[0]
        total_qualified = self.conn.execute("SELECT COUNT(*) FROM businesses WHERE processing_status = 'QUALIFIED';").fetchone()[0]
        total_runs = self.conn.execute("SELECT COUNT(*) FROM pipeline_runs;").fetchone()[0]
        no_websites = self.conn.execute("SELECT COUNT(*) FROM businesses WHERE website IS NULL OR website = '' OR website_status = 'NO_WEBSITE';").fetchone()[0]

        # Tier breakdown
        tiers = {"A+": 0, "A": 0, "B": 0, "C": 0, "D": 0}
        for r in self.conn.execute("SELECT tier, COUNT(*) FROM lead_scores GROUP BY tier;").fetchall():
            if r[0] in tiers:
                tiers[r[0]] = r[1]

        # Top recommended services
        services = []
        for r in self.conn.execute("SELECT recommended_service, COUNT(*) as c FROM lead_scores WHERE recommended_service != 'NONE' GROUP BY recommended_service ORDER BY c DESC LIMIT 6;").fetchall():
            services.append({"name": r[0], "count": r[1]})

        # Vertical distribution
        vert_counts = []
        for r in self.conn.execute("SELECT vertical, COUNT(*) as c FROM businesses GROUP BY vertical ORDER BY c DESC;").fetchall():
            vert_counts.append({"name": r[0].title(), "count": r[1]})

        # Score distribution histogram (buckets: 0-19, 20-39, 40-59, 60-79, 80-100)
        buckets = [
            {"range": "0–19", "count": 0},
            {"range": "20–39", "count": 0},
            {"range": "40–59", "count": 0},
            {"range": "60–79", "count": 0},
            {"range": "80–100", "count": 0},
        ]
        for r in self.conn.execute("SELECT total_score FROM lead_scores;").fetchall():
            val = r[0]
            if val < 20:
                buckets[0]["count"] += 1
            elif val < 40:
                buckets[1]["count"] += 1
            elif val < 60:
                buckets[2]["count"] += 1
            elif val < 80:
                buckets[3]["count"] += 1
            else:
                buckets[4]["count"] += 1

        # Recent scans
        recent_scans = []
        for r in self.conn.execute("SELECT id, market, vertical, status, target, qualified, exported, started_at, finished_at FROM pipeline_runs ORDER BY id DESC LIMIT 5;").fetchall():
            recent_scans.append({
                "id": r["id"],
                "market": r["market"],
                "vertical": r["vertical"],
                "status": r["status"],
                "target": r["target"],
                "qualified": r["qualified"],
                "exported": r["exported"],
                "started_at": r["started_at"],
                "finished_at": r["finished_at"],
            })

        return {
            "total_businesses": total_biz,
            "qualified_leads": total_qualified,
            "a_plus_leads": tiers["A+"],
            "a_leads": tiers["A"],
            "b_leads": tiers["B"],
            "no_website_leads": no_websites,
            "completed_scans": total_runs,
            "tiers": tiers,
            "services": services,
            "verticals": vert_counts,
            "score_distribution": buckets,
            "recent_scans": recent_scans,
        }



class WebsiteProfileRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def upsert(self, p: WebsiteProfile) -> int:
        schema_types_str = ",".join(p.schema_types) if p.schema_types else ""
        analytics_str = ",".join(p.analytics_providers) if p.analytics_providers else ""
        tech_json = json.dumps(p.detected_technologies) if p.detected_technologies else "[]"

        cur = self.conn.execute(
            """
            INSERT INTO website_profiles (
                business_id, requested_url, final_url, domain, http_status, https_enabled, reachable, redirect_count,
                html_title, meta_description, canonical_url, has_viewport, has_h1, h1_count,
                has_robots_txt, has_sitemap, has_schema, schema_types, has_open_graph,
                has_analytics, analytics_providers, has_contact_page, contact_page_url,
                has_booking, booking_url, has_menu, menu_url, menu_is_pdf,
                has_phone_on_site, has_email_on_site, detected_technologies_json,
                page_count_crawled, crawl_duration_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(business_id) DO UPDATE SET
                requested_url=excluded.requested_url,
                final_url=excluded.final_url,
                domain=excluded.domain,
                http_status=excluded.http_status,
                https_enabled=excluded.https_enabled,
                reachable=excluded.reachable,
                redirect_count=excluded.redirect_count,
                html_title=excluded.html_title,
                meta_description=excluded.meta_description,
                canonical_url=excluded.canonical_url,
                has_viewport=excluded.has_viewport,
                has_h1=excluded.has_h1,
                h1_count=excluded.h1_count,
                has_robots_txt=excluded.has_robots_txt,
                has_sitemap=excluded.has_sitemap,
                has_schema=excluded.has_schema,
                schema_types=excluded.schema_types,
                has_open_graph=excluded.has_open_graph,
                has_analytics=excluded.has_analytics,
                analytics_providers=excluded.analytics_providers,
                has_contact_page=excluded.has_contact_page,
                contact_page_url=excluded.contact_page_url,
                has_booking=excluded.has_booking,
                booking_url=excluded.booking_url,
                has_menu=excluded.has_menu,
                menu_url=excluded.menu_url,
                menu_is_pdf=excluded.menu_is_pdf,
                has_phone_on_site=excluded.has_phone_on_site,
                has_email_on_site=excluded.has_email_on_site,
                detected_technologies_json=excluded.detected_technologies_json,
                page_count_crawled=excluded.page_count_crawled,
                crawl_duration_ms=excluded.crawl_duration_ms,
                updated_at=CURRENT_TIMESTAMP
            """,
            (
                p.business_id, p.requested_url, p.final_url, p.domain, p.http_status,
                1 if p.https_enabled else 0, 1 if p.reachable else 0, p.redirect_count,
                p.html_title, p.meta_description, p.canonical_url,
                1 if p.has_viewport else 0, 1 if p.has_h1 else 0, p.h1_count,
                1 if p.has_robots_txt else 0, 1 if p.has_sitemap else 0,
                1 if p.has_schema else 0, schema_types_str, 1 if p.has_open_graph else 0,
                1 if p.has_analytics else 0, analytics_str,
                1 if p.has_contact_page else 0, p.contact_page_url,
                1 if p.has_booking else 0, p.booking_url,
                1 if p.has_menu else 0, p.menu_url, 1 if p.menu_is_pdf else 0,
                1 if p.has_phone_on_site else 0, 1 if p.has_email_on_site else 0,
                tech_json, p.page_count_crawled, p.crawl_duration_ms
            ),
        )
        if cur.lastrowid:
            p.id = cur.lastrowid
        return p.id or 0

    def get_by_business_id(self, business_id: int) -> Optional[WebsiteProfile]:
        cur = self.conn.execute("SELECT * FROM website_profiles WHERE business_id = ?;", (business_id,))
        row = cur.fetchone()
        if not row:
            return None

        schema_types = [s.strip() for s in (row["schema_types"] or "").split(",") if s.strip()]
        analytics = [a.strip() for a in (row["analytics_providers"] or "").split(",") if a.strip()]
        try:
            tech = json.loads(row["detected_technologies_json"] or "[]")
        except Exception:
            tech = []

        return WebsiteProfile(
            id=row["id"],
            business_id=row["business_id"],
            requested_url=row["requested_url"],
            final_url=row["final_url"],
            domain=row["domain"],
            http_status=row["http_status"],
            https_enabled=bool(row["https_enabled"]),
            reachable=bool(row["reachable"]),
            redirect_count=row["redirect_count"],
            html_title=row["html_title"],
            meta_description=row["meta_description"],
            canonical_url=row["canonical_url"],
            has_viewport=bool(row["has_viewport"]),
            has_h1=bool(row["has_h1"]),
            h1_count=row["h1_count"],
            has_robots_txt=bool(row["has_robots_txt"]),
            has_sitemap=bool(row["has_sitemap"]),
            has_schema=bool(row["has_schema"]),
            schema_types=schema_types,
            has_open_graph=bool(row["has_open_graph"]),
            has_analytics=bool(row["has_analytics"]),
            analytics_providers=analytics,
            has_contact_page=bool(row["has_contact_page"]),
            contact_page_url=row["contact_page_url"],
            has_booking=bool(row["has_booking"]),
            booking_url=row["booking_url"],
            has_menu=bool(row["has_menu"]),
            menu_url=row["menu_url"],
            menu_is_pdf=bool(row["menu_is_pdf"]),
            has_phone_on_site=bool(row["has_phone_on_site"]),
            has_email_on_site=bool(row["has_email_on_site"]),
            detected_technologies=tech,
            page_count_crawled=row["page_count_crawled"],
            crawl_duration_ms=row["crawl_duration_ms"],
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"]),
        )


class ContactRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def insert(self, c: Contact) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO contacts (
                business_id, contact_type, contact_value, source_url, source_type,
                confidence, is_public_business_contact, is_valid
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                c.business_id, c.contact_type, c.contact_value, c.source_url, c.source_type,
                c.confidence, 1 if c.is_public_business_contact else 0, 1 if c.is_valid else 0
            ),
        )
        c.id = cur.lastrowid
        return c.id

    def list_by_business_id(self, business_id: int) -> List[Contact]:
        cur = self.conn.execute("SELECT * FROM contacts WHERE business_id = ? ORDER BY id ASC;", (business_id,))
        return [
            Contact(
                id=r["id"],
                business_id=r["business_id"],
                contact_type=r["contact_type"],
                contact_value=r["contact_value"],
                source_url=r["source_url"],
                source_type=r["source_type"],
                confidence=r["confidence"],
                is_public_business_contact=bool(r["is_public_business_contact"]),
                is_valid=bool(r["is_valid"]),
                created_at=str(r["created_at"]),
            )
            for r in cur.fetchall()
        ]

    def delete_by_business_id(self, business_id: int) -> None:
        self.conn.execute("DELETE FROM contacts WHERE business_id = ?;", (business_id,))


class LighthouseRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def upsert(self, lh: LighthouseResult) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO lighthouse_results (
                business_id, performance_score, seo_score, accessibility_score, best_practices_score,
                lcp_ms, cls, tbt_ms, fcp_ms, speed_index_ms, raw_report_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(business_id) DO UPDATE SET
                performance_score=excluded.performance_score,
                seo_score=excluded.seo_score,
                accessibility_score=excluded.accessibility_score,
                best_practices_score=excluded.best_practices_score,
                lcp_ms=excluded.lcp_ms,
                cls=excluded.cls,
                tbt_ms=excluded.tbt_ms,
                fcp_ms=excluded.fcp_ms,
                speed_index_ms=excluded.speed_index_ms,
                raw_report_path=excluded.raw_report_path,
                created_at=CURRENT_TIMESTAMP
            """,
            (
                lh.business_id, lh.performance_score, lh.seo_score, lh.accessibility_score,
                lh.best_practices_score, lh.lcp_ms, lh.cls, lh.tbt_ms, lh.fcp_ms,
                lh.speed_index_ms, lh.raw_report_path
            ),
        )
        if cur.lastrowid:
            lh.id = cur.lastrowid
        return lh.id or 0

    def get_by_business_id(self, business_id: int) -> Optional[LighthouseResult]:
        cur = self.conn.execute("SELECT * FROM lighthouse_results WHERE business_id = ?;", (business_id,))
        row = cur.fetchone()
        if not row:
            return None
        return LighthouseResult(
            id=row["id"],
            business_id=row["business_id"],
            performance_score=row["performance_score"],
            seo_score=row["seo_score"],
            accessibility_score=row["accessibility_score"],
            best_practices_score=row["best_practices_score"],
            lcp_ms=row["lcp_ms"],
            cls=row["cls"],
            tbt_ms=row["tbt_ms"],
            fcp_ms=row["fcp_ms"],
            speed_index_ms=row["speed_index_ms"],
            raw_report_path=row["raw_report_path"],
            created_at=str(row["created_at"]),
        )


class FindingRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def insert_batch(self, findings: List[Finding]) -> None:
        for f in findings:
            cur = self.conn.execute(
                """
                INSERT INTO findings (
                    business_id, finding_code, category, severity, title, description,
                    evidence, source_url, score_points
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f.business_id, f.finding_code, f.category, f.severity, f.title,
                    f.description, f.evidence, f.source_url, f.score_points
                ),
            )
            f.id = cur.lastrowid

    def list_by_business_id(self, business_id: int) -> List[Finding]:
        cur = self.conn.execute(
            "SELECT * FROM findings WHERE business_id = ? ORDER BY score_points DESC, id ASC;",
            (business_id,),
        )
        return [
            Finding(
                id=r["id"],
                business_id=r["business_id"],
                finding_code=r["finding_code"],
                category=r["category"],
                severity=r["severity"],
                title=r["title"],
                description=r["description"],
                evidence=r["evidence"],
                source_url=r["source_url"],
                score_points=r["score_points"],
                created_at=str(r["created_at"]),
            )
            for r in cur.fetchall()
        ]

    def delete_by_business_id(self, business_id: int) -> None:
        self.conn.execute("DELETE FROM findings WHERE business_id = ?;", (business_id,))


class LeadScoreRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def upsert(self, ls: LeadScore) -> None:
        breakdown_json = json.dumps(ls.score_breakdown) if ls.score_breakdown else "{}"
        self.conn.execute(
            """
            INSERT INTO lead_scores (
                business_id, total_score, tier, website_score, seo_opportunity_score,
                vertical_opportunity_score, contactability_score, recommended_service,
                recommended_angle, score_breakdown_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(business_id) DO UPDATE SET
                total_score=excluded.total_score,
                tier=excluded.tier,
                website_score=excluded.website_score,
                seo_opportunity_score=excluded.seo_opportunity_score,
                vertical_opportunity_score=excluded.vertical_opportunity_score,
                contactability_score=excluded.contactability_score,
                recommended_service=excluded.recommended_service,
                recommended_angle=excluded.recommended_angle,
                score_breakdown_json=excluded.score_breakdown_json,
                calculated_at=CURRENT_TIMESTAMP
            """,
            (
                ls.business_id, ls.total_score, ls.tier, ls.website_score,
                ls.seo_opportunity_score, ls.vertical_opportunity_score,
                ls.contactability_score, ls.recommended_service, ls.recommended_angle,
                breakdown_json
            ),
        )

    def get_by_business_id(self, business_id: int) -> Optional[LeadScore]:
        cur = self.conn.execute("SELECT * FROM lead_scores WHERE business_id = ?;", (business_id,))
        row = cur.fetchone()
        if not row:
            return None
        try:
            breakdown = json.loads(row["score_breakdown_json"] or "{}")
        except Exception:
            breakdown = {}

        return LeadScore(
            business_id=row["business_id"],
            total_score=row["total_score"],
            tier=row["tier"],
            website_score=row["website_score"],
            seo_opportunity_score=row["seo_opportunity_score"],
            vertical_opportunity_score=row["vertical_opportunity_score"],
            contactability_score=row["contactability_score"],
            recommended_service=row["recommended_service"],
            recommended_angle=row["recommended_angle"],
            score_breakdown=breakdown,
            calculated_at=str(row["calculated_at"]),
        )

    def get_ranked_leads(self, tiers: Optional[List[str]] = None, limit: Optional[int] = None) -> List[Tuple[Business, LeadScore]]:
        """Get businesses joined with lead_scores, sorted by total_score DESC, contactability DESC, source_confidence DESC."""
        query = """
            SELECT b.*, ls.total_score, ls.tier, ls.website_score, ls.seo_opportunity_score,
                   ls.vertical_opportunity_score, ls.contactability_score,
                   ls.recommended_service, ls.recommended_angle, ls.score_breakdown_json, ls.calculated_at
            FROM businesses b
            JOIN lead_scores ls ON b.id = ls.business_id
            WHERE b.is_rejected = 0 AND b.is_duplicate = 0
        """
        params: List[Any] = []
        if tiers:
            placeholders = ",".join("?" for _ in tiers)
            query += f" AND ls.tier IN ({placeholders})"
            params.extend(tiers)

        query += " ORDER BY ls.total_score DESC, ls.contactability_score DESC, b.source_confidence DESC"
        if limit:
            query += f" LIMIT {int(limit)}"

        cur = self.conn.execute(query, params)
        results = []
        for r in cur.fetchall():
            b = Business(
                id=r["id"],
                external_overture_id=r["external_overture_id"],
                external_osm_id=r["external_osm_id"],
                name=r["name"],
                normalized_name=r["normalized_name"],
                vertical=r["vertical"],
                subcategory=r["subcategory"],
                country=r["country"],
                country_code=r["country_code"],
                state=r["state"],
                city=r["city"],
                postcode=r["postcode"],
                address=r["address"],
                latitude=r["latitude"],
                longitude=r["longitude"],
                phone=r["phone"],
                normalized_phone=r["normalized_phone"],
                website=r["website"],
                domain=r["domain"],
                public_email=r["public_email"],
                instagram=r["instagram"],
                facebook=r["facebook"],
                linkedin=r["linkedin"],
                x_url=r["x_url"],
                source_overture=bool(r["source_overture"]),
                source_osm=bool(r["source_osm"]),
                source_confidence=r["source_confidence"],
                operating_status=r["operating_status"],
                is_chain=bool(r["is_chain"]),
                is_duplicate=bool(r["is_duplicate"]),
                is_rejected=bool(r["is_rejected"]),
                rejection_reason=r["rejection_reason"],
                processing_status=r["processing_status"],
            )
            try:
                breakdown = json.loads(r["score_breakdown_json"] or "{}")
            except Exception:
                breakdown = {}
            ls = LeadScore(
                business_id=r["id"],
                total_score=r["total_score"],
                tier=r["tier"],
                website_score=r["website_score"],
                seo_opportunity_score=r["seo_opportunity_score"],
                vertical_opportunity_score=r["vertical_opportunity_score"],
                contactability_score=r["contactability_score"],
                recommended_service=r["recommended_service"],
                recommended_angle=r["recommended_angle"],
                score_breakdown=breakdown,
                calculated_at=str(r["calculated_at"]),
            )
            results.append((b, ls))
        return results


class PipelineRunRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, run: PipelineRun) -> int:
        config_json = json.dumps(run.run_configuration) if run.run_configuration else None
        cur = self.conn.execute(
            """
            INSERT INTO pipeline_runs (market, vertical, target, status, run_configuration_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (run.market, run.vertical, run.target, run.status, config_json),
        )
        run.id = cur.lastrowid
        return run.id

    def update(self, run: PipelineRun) -> None:
        config_json = json.dumps(run.run_configuration) if run.run_configuration else None
        self.conn.execute(
            """
            UPDATE pipeline_runs SET
                finished_at = ?, status = ?, raw_found = ?, deduped = ?,
                filtered = ?, websites_processed = ?, qualified = ?, exported = ?,
                output_file = ?, error_message = ?, run_configuration_json = ?,
                cancelled_at = ?
            WHERE id = ?
            """,
            (
                run.finished_at, run.status, run.raw_found, run.deduped,
                run.filtered, run.websites_processed, run.qualified, run.exported,
                run.output_file, run.error_message, config_json, run.cancelled_at, run.id
            ),
        )

    def cancel_run(self, run_id: int) -> bool:
        cur = self.conn.execute(
            """
            UPDATE pipeline_runs SET
                status = 'CANCELLED',
                cancellation_requested = 1,
                cancelled_at = CURRENT_TIMESTAMP,
                finished_at = CURRENT_TIMESTAMP
            WHERE id = ? AND status IN ('RUNNING', 'QUEUED');
            """,
            (run_id,)
        )
        return cur.rowcount > 0

    def get_by_id(self, run_id: int) -> Optional[PipelineRun]:
        cur = self.conn.execute("SELECT * FROM pipeline_runs WHERE id = ?;", (run_id,))
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_run(row)

    def get_latest(self) -> Optional[PipelineRun]:
        cur = self.conn.execute("SELECT * FROM pipeline_runs ORDER BY id DESC LIMIT 1;")
        row = cur.fetchone()
        if not row:
            return None
        return self._row_to_run(row)

    def list_runs(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None,
        vertical: Optional[str] = None,
    ) -> Tuple[List[PipelineRun], int]:
        conditions = []
        params = []
        if status:
            conditions.append("status = ?")
            params.append(status.upper())
        if vertical:
            conditions.append("vertical = ?")
            params.append(vertical.lower())

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        total = self.conn.execute(f"SELECT COUNT(*) FROM pipeline_runs {where};", params).fetchone()[0]

        limit = max(page_size, 1)
        offset = max((page - 1) * limit, 0)
        cur = self.conn.execute(
            f"SELECT * FROM pipeline_runs {where} ORDER BY id DESC LIMIT ? OFFSET ?;",
            params + [limit, offset],
        )
        runs = [self._row_to_run(r) for r in cur.fetchall()]
        return runs, total

    def _row_to_run(self, row: sqlite3.Row) -> PipelineRun:
        keys = row.keys()
        cfg = None
        if "run_configuration_json" in keys and row["run_configuration_json"]:
            try:
                cfg = json.loads(row["run_configuration_json"])
            except Exception:
                cfg = None

        return PipelineRun(
            id=row["id"],
            market=row["market"],
            vertical=row["vertical"],
            target=row["target"],
            started_at=str(row["started_at"]) if row["started_at"] else None,
            finished_at=str(row["finished_at"]) if row["finished_at"] else None,
            status=row["status"],
            raw_found=row["raw_found"],
            deduped=row["deduped"],
            filtered=row["filtered"],
            websites_processed=row["websites_processed"],
            qualified=row["qualified"],
            exported=row["exported"],
            output_file=row["output_file"],
            error_message=row["error_message"],
            run_configuration=cfg,
            cancelled_at=str(row["cancelled_at"]) if "cancelled_at" in keys and row["cancelled_at"] else None,
        )


class PipelineRunEventRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create(self, event: PipelineRunEvent) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO pipeline_run_events (
                run_id, stage, event_type, message, completed, total, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.run_id, event.stage, event.event_type, event.message,
                event.completed, event.total, event.metadata_json
            ),
        )
        event.id = cur.lastrowid
        return event.id

    insert = create

    def list_by_run(
        self,
        run_id: int,
        after_id: Optional[int] = None,
        limit: int = 200,
    ) -> List[PipelineRunEvent]:
        if after_id is not None:
            cur = self.conn.execute(
                """
                SELECT * FROM pipeline_run_events
                WHERE run_id = ? AND id > ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (run_id, after_id, limit),
            )
        else:
            cur = self.conn.execute(
                """
                SELECT * FROM pipeline_run_events
                WHERE run_id = ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (run_id, limit),
            )

        return [
            PipelineRunEvent(
                id=r["id"],
                run_id=r["run_id"],
                timestamp=str(r["timestamp"]),
                stage=r["stage"],
                event_type=r["event_type"],
                message=r["message"],
                completed=r["completed"],
                total=r["total"],
                metadata_json=r["metadata_json"],
            )
            for r in cur.fetchall()
        ]

    def get_latest(self, run_id: int) -> Optional[PipelineRunEvent]:
        cur = self.conn.execute(
            "SELECT * FROM pipeline_run_events WHERE run_id = ? ORDER BY id DESC LIMIT 1;",
            (run_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return PipelineRunEvent(
            id=row["id"],
            run_id=row["run_id"],
            timestamp=str(row["timestamp"]),
            stage=row["stage"],
            event_type=row["event_type"],
            message=row["message"],
            completed=row["completed"],
            total=row["total"],
            metadata_json=row["metadata_json"],
        )

