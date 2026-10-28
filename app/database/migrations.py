from app.database.phase41_schema import PHASE41_SQL
import logging
import sqlite3
from typing import List

from app.database.connection import get_connection

logger = logging.getLogger("leadengine.migrations")
from app.database.phase3_schema import PHASE3_SQL
from app.database.phase35_schema import PHASE35_SQL,apply_phase35
from app.database.phase36_schema import PHASE36_SQL
from app.database.phase4_schema import PHASE4_SQL,apply_phase4

MIGRATIONS: List[str] = [
    # Migration 1: Initial schema
    """
    CREATE TABLE IF NOT EXISTS schema_migrations (
        version INTEGER PRIMARY KEY,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS businesses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        external_overture_id TEXT,
        external_osm_id TEXT,

        name TEXT NOT NULL,
        normalized_name TEXT NOT NULL,

        vertical TEXT NOT NULL,
        subcategory TEXT,

        country TEXT,
        country_code TEXT,
        state TEXT,
        city TEXT,
        postcode TEXT,
        address TEXT,

        latitude REAL,
        longitude REAL,

        phone TEXT,
        normalized_phone TEXT,

        website TEXT,
        domain TEXT,

        public_email TEXT,

        instagram TEXT,
        facebook TEXT,
        linkedin TEXT,
        x_url TEXT,

        source_overture INTEGER DEFAULT 0,
        source_osm INTEGER DEFAULT 0,
        source_confidence REAL DEFAULT 0.5,
        operating_status TEXT DEFAULT 'active',

        is_chain INTEGER DEFAULT 0,
        is_duplicate INTEGER DEFAULT 0,
        is_rejected INTEGER DEFAULT 0,
        rejection_reason TEXT,
        processing_status TEXT DEFAULT 'DISCOVERED',

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_businesses_domain ON businesses(domain);
    CREATE INDEX IF NOT EXISTS idx_businesses_norm_name ON businesses(normalized_name);
    CREATE INDEX IF NOT EXISTS idx_businesses_norm_phone ON businesses(normalized_phone);
    CREATE INDEX IF NOT EXISTS idx_businesses_vertical ON businesses(vertical);
    CREATE INDEX IF NOT EXISTS idx_businesses_status ON businesses(processing_status);
    CREATE INDEX IF NOT EXISTS idx_businesses_rejected ON businesses(is_rejected);
    CREATE INDEX IF NOT EXISTS idx_businesses_chain ON businesses(is_chain);

    CREATE TABLE IF NOT EXISTS website_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        business_id INTEGER NOT NULL UNIQUE,

        requested_url TEXT NOT NULL,
        final_url TEXT,
        domain TEXT,

        http_status INTEGER,
        https_enabled INTEGER DEFAULT 0,
        reachable INTEGER DEFAULT 0,
        redirect_count INTEGER DEFAULT 0,

        html_title TEXT,
        meta_description TEXT,
        canonical_url TEXT,

        has_viewport INTEGER DEFAULT 0,
        has_h1 INTEGER DEFAULT 0,
        h1_count INTEGER DEFAULT 0,

        has_robots_txt INTEGER DEFAULT 0,
        has_sitemap INTEGER DEFAULT 0,

        has_schema INTEGER DEFAULT 0,
        schema_types TEXT, -- comma-separated

        has_open_graph INTEGER DEFAULT 0,

        has_analytics INTEGER DEFAULT 0,
        analytics_providers TEXT, -- comma-separated

        has_contact_page INTEGER DEFAULT 0,
        contact_page_url TEXT,

        has_booking INTEGER DEFAULT 0,
        booking_url TEXT,

        has_menu INTEGER DEFAULT 0,
        menu_url TEXT,
        menu_is_pdf INTEGER DEFAULT 0,

        has_phone_on_site INTEGER DEFAULT 0,
        has_email_on_site INTEGER DEFAULT 0,

        detected_technologies_json TEXT,

        page_count_crawled INTEGER DEFAULT 0,
        crawl_duration_ms INTEGER DEFAULT 0,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_web_profiles_business_id ON website_profiles(business_id);
    CREATE INDEX IF NOT EXISTS idx_web_profiles_reachable ON website_profiles(reachable);

    CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        business_id INTEGER NOT NULL,

        contact_type TEXT NOT NULL, -- email, phone, contact_form, instagram, facebook, linkedin, booking
        contact_value TEXT NOT NULL,

        source_url TEXT,
        source_type TEXT DEFAULT 'WEBSITE',

        confidence REAL DEFAULT 1.0,
        is_public_business_contact INTEGER DEFAULT 1,
        is_valid INTEGER DEFAULT 1,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_contacts_business_id ON contacts(business_id);
    CREATE INDEX IF NOT EXISTS idx_contacts_type ON contacts(contact_type);

    CREATE TABLE IF NOT EXISTS lighthouse_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        business_id INTEGER NOT NULL UNIQUE,

        performance_score REAL,
        seo_score REAL,
        accessibility_score REAL,
        best_practices_score REAL,

        lcp_ms REAL,
        cls REAL,
        tbt_ms REAL,
        fcp_ms REAL,
        speed_index_ms REAL,

        raw_report_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_lighthouse_business_id ON lighthouse_results(business_id);

    CREATE TABLE IF NOT EXISTS findings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        business_id INTEGER NOT NULL,

        finding_code TEXT NOT NULL,
        category TEXT NOT NULL,
        severity TEXT NOT NULL,

        title TEXT NOT NULL,
        description TEXT NOT NULL,

        evidence TEXT,
        source_url TEXT,

        score_points INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_findings_business_id ON findings(business_id);
    CREATE INDEX IF NOT EXISTS idx_findings_code ON findings(finding_code);

    CREATE TABLE IF NOT EXISTS lead_scores (
        business_id INTEGER PRIMARY KEY,

        total_score REAL NOT NULL,
        tier TEXT NOT NULL,

        website_score REAL DEFAULT 0,
        seo_opportunity_score REAL DEFAULT 0,
        vertical_opportunity_score REAL DEFAULT 0,
        contactability_score REAL DEFAULT 0,

        recommended_service TEXT,
        recommended_angle TEXT,

        score_breakdown_json TEXT,
        calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_lead_scores_total ON lead_scores(total_score);
    CREATE INDEX IF NOT EXISTS idx_lead_scores_tier ON lead_scores(tier);

    CREATE TABLE IF NOT EXISTS pipeline_runs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        market TEXT NOT NULL,
        vertical TEXT NOT NULL,
        target INTEGER NOT NULL,

        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        finished_at TIMESTAMP,

        status TEXT DEFAULT 'RUNNING',

        raw_found INTEGER DEFAULT 0,
        deduped INTEGER DEFAULT 0,
        filtered INTEGER DEFAULT 0,
        websites_processed INTEGER DEFAULT 0,
        qualified INTEGER DEFAULT 0,
        exported INTEGER DEFAULT 0,

        output_file TEXT,
        error_message TEXT
    );
    """,
    # Migration 2: Phase 2 Quality Hardening & Real-Time Pipeline Events
    """
    ALTER TABLE businesses ADD COLUMN source_category TEXT;
    ALTER TABLE businesses ADD COLUMN source_tags_json TEXT;
    ALTER TABLE businesses ADD COLUMN vertical_validation_status TEXT DEFAULT 'VALID';
    ALTER TABLE businesses ADD COLUMN vertical_validation_reason TEXT;
    ALTER TABLE businesses ADD COLUMN vertical_validation_confidence REAL DEFAULT 1.0;
    ALTER TABLE businesses ADD COLUMN chain_reason TEXT;
    ALTER TABLE businesses ADD COLUMN chain_confidence REAL DEFAULT 0.0;
    ALTER TABLE businesses ADD COLUMN website_status TEXT;

    CREATE INDEX IF NOT EXISTS idx_businesses_vert_val ON businesses(vertical_validation_status);
    CREATE INDEX IF NOT EXISTS idx_businesses_web_status ON businesses(website_status);

    ALTER TABLE pipeline_runs ADD COLUMN run_configuration_json TEXT;
    ALTER TABLE pipeline_runs ADD COLUMN cancelled_at TIMESTAMP;

    CREATE TABLE IF NOT EXISTS pipeline_run_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id INTEGER NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        stage TEXT NOT NULL,
        event_type TEXT NOT NULL,
        message TEXT NOT NULL,
        completed INTEGER DEFAULT 0,
        total INTEGER DEFAULT 0,
        metadata_json TEXT,

        FOREIGN KEY (run_id) REFERENCES pipeline_runs(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_pipeline_events_run_id ON pipeline_run_events(run_id);
    CREATE INDEX IF NOT EXISTS idx_pipeline_events_time ON pipeline_run_events(timestamp);
    """,
    # Migration 3: Add run_id to businesses and additional indexes for query optimization
    """
    ALTER TABLE businesses ADD COLUMN run_id INTEGER;

    CREATE INDEX IF NOT EXISTS idx_businesses_run_id ON businesses(run_id);
    CREATE INDEX IF NOT EXISTS idx_businesses_city ON businesses(city);
    CREATE INDEX IF NOT EXISTS idx_businesses_state ON businesses(state);
    CREATE INDEX IF NOT EXISTS idx_businesses_country ON businesses(country);
    """
    , PHASE3_SQL,PHASE35_SQL,PHASE36_SQL,PHASE4_SQL,PHASE41_SQL
]


def run_migrations(conn: sqlite3.Connection = None) -> int:
    """Run pending SQLite migrations. Returns number of migrations applied."""
    close_when_done = False
    if conn is None:
        conn = get_connection()
        close_when_done = True

    try:
        postgres = getattr(conn, "backend", None) == "postgres"
        if postgres:
            conn.execute("SELECT pg_advisory_xact_lock(691944301)")
        # Check current version
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        cur = conn.execute("SELECT MAX(version) FROM schema_migrations;")
        current_version = cur.fetchone()[0] or 0

        applied_count = 0
        for i, migration_sql in enumerate(MIGRATIONS, start=1):
            if i > current_version:
                logger.info(f"Applying database migration #{i}...")
                if postgres:
                    import re
                    migration_sql = re.sub(r"INTEGER PRIMARY KEY AUTOINCREMENT", "BIGSERIAL PRIMARY KEY", migration_sql)
                    # Historical models store ISO strings; TEXT avoids implicit timestamp casts.
                    migration_sql = migration_sql.replace("TIMESTAMP DEFAULT CURRENT_TIMESTAMP", "TEXT DEFAULT (CURRENT_TIMESTAMP::text)")
                if i==7:apply_phase4(conn,postgres)
                elif i==5:apply_phase35(conn,postgres)
                else:conn.executescript(migration_sql)
                if i==8:
                    from app.mail.tracking import backfill
                    backfill(conn)
                conn.execute("INSERT INTO schema_migrations (version) VALUES (?);", (i,))
                if not postgres:
                    conn.commit()
                applied_count += 1
                logger.info(f"Migration #{i} applied successfully.")

        conn.commit()
        return applied_count
    finally:
        if close_when_done:
            conn.close()


def verify_schema(conn=None,minimum_version=None):
    """Production only checks schema version; migrations run explicitly at release."""
    close = conn is None
    conn = conn or get_connection()
    try:
        version = conn.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0]
        if not (minimum_version or len(MIGRATIONS)) <= (version or 0) <= len(MIGRATIONS):
            raise RuntimeError("Database schema is out of date; run the explicit migration command")
    finally:
        if close:
            conn.close()
