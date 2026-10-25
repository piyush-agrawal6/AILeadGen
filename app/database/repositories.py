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
    ProcessingStatus,
)


class BusinessRepository:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def insert(self, b: Business) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO businesses (
                external_overture_id, external_osm_id, name, normalized_name,
                vertical, subcategory, country, country_code, state, city, postcode, address,
                latitude, longitude, phone, normalized_phone, website, domain,
                public_email, instagram, facebook, linkedin, x_url,
                source_overture, source_osm, source_confidence, operating_status,
                is_chain, is_duplicate, is_rejected, rejection_reason, processing_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                b.external_overture_id, b.external_osm_id, b.name, b.normalized_name,
                b.vertical, b.subcategory, b.country, b.country_code, b.state, b.city, b.postcode, b.address,
                b.latitude, b.longitude, b.phone, b.normalized_phone, b.website, b.domain,
                b.public_email, b.instagram, b.facebook, b.linkedin, b.x_url,
                1 if b.source_overture else 0, 1 if b.source_osm else 0, b.source_confidence, b.operating_status,
                1 if b.is_chain else 0, 1 if b.is_duplicate else 0, 1 if b.is_rejected else 0,
                b.rejection_reason, b.processing_status
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
                external_overture_id = ?, external_osm_id = ?, name = ?, normalized_name = ?,
                vertical = ?, subcategory = ?, country = ?, country_code = ?, state = ?, city = ?, postcode = ?, address = ?,
                latitude = ?, longitude = ?, phone = ?, normalized_phone = ?, website = ?, domain = ?,
                public_email = ?, instagram = ?, facebook = ?, linkedin = ?, x_url = ?,
                source_overture = ?, source_osm = ?, source_confidence = ?, operating_status = ?,
                is_chain = ?, is_duplicate = ?, is_rejected = ?, rejection_reason = ?, processing_status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                b.external_overture_id, b.external_osm_id, b.name, b.normalized_name,
                b.vertical, b.subcategory, b.country, b.country_code, b.state, b.city, b.postcode, b.address,
                b.latitude, b.longitude, b.phone, b.normalized_phone, b.website, b.domain,
                b.public_email, b.instagram, b.facebook, b.linkedin, b.x_url,
                1 if b.source_overture else 0, 1 if b.source_osm else 0, b.source_confidence, b.operating_status,
                1 if b.is_chain else 0, 1 if b.is_duplicate else 0, 1 if b.is_rejected else 0,
                b.rejection_reason, b.processing_status, b.id
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
        return Business(
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
            created_at=str(r["created_at"]),
            updated_at=str(r["updated_at"]),
        )


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
        cur = self.conn.execute(
            """
            INSERT INTO pipeline_runs (market, vertical, target, status)
            VALUES (?, ?, ?, ?)
            """,
            (run.market, run.vertical, run.target, run.status),
        )
        run.id = cur.lastrowid
        return run.id

    def update(self, run: PipelineRun) -> None:
        self.conn.execute(
            """
            UPDATE pipeline_runs SET
                finished_at = ?, status = ?, raw_found = ?, deduped = ?,
                filtered = ?, websites_processed = ?, qualified = ?, exported = ?,
                output_file = ?, error_message = ?
            WHERE id = ?
            """,
            (
                run.finished_at, run.status, run.raw_found, run.deduped,
                run.filtered, run.websites_processed, run.qualified, run.exported,
                run.output_file, run.error_message, run.id
            ),
        )

    def get_by_id(self, run_id: int) -> Optional[PipelineRun]:
        cur = self.conn.execute("SELECT * FROM pipeline_runs WHERE id = ?;", (run_id,))
        row = cur.fetchone()
        if not row:
            return None
        return PipelineRun(
            id=row["id"],
            market=row["market"],
            vertical=row["vertical"],
            target=row["target"],
            started_at=str(row["started_at"]),
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
        )

    def get_latest(self) -> Optional[PipelineRun]:
        cur = self.conn.execute("SELECT * FROM pipeline_runs ORDER BY id DESC LIMIT 1;")
        row = cur.fetchone()
        if not row:
            return None
        return self.get_by_id(row["id"])
