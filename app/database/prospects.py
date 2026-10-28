"""Canonical identities and lightweight collaboration, independent of observations."""
import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse


def now():
    return datetime.now(timezone.utc).isoformat()


def normalize(value):
    return re.sub(r"\W+", " ", (value or "").casefold()).strip()


def identity_keys(business):
    keys = []
    for source in ("external_overture_id", "external_osm_id"):
        if value := getattr(business, source, None):
            keys.append((source + ":" + value, "SOURCE_ID"))
    phone = re.sub(r"\D", "", business.normalized_phone or business.phone or "")
    location = "|".join(normalize(value) for value in [business.address, business.city, business.country_code or business.country])
    host = (urlparse(business.website or "").hostname or business.domain or "").lower().removeprefix("www.")
    # Hosted website platforms are scoped to the tenant URL, not their shared root.
    if any(host == x or host.endswith("." + x) for x in ["wixsite.com", "square.site", "wordpress.com", "webflow.io", "squarespace.com"]):
        host += urlparse(business.website or "").path.rstrip("/")
    if host:
        # Corporate roots can host several distinct venues in the same city.
        # Require the street address as well when discovery supplied one.
        keys.append((f"domain:{host}|{normalize(business.city)}|{normalize(business.country_code or business.country)}|{normalize(business.address)}", "DOMAIN_LOCATION"))
    if len(phone) >= 8:
        keys.append((f"phone:{phone}|{normalize(business.normalized_name)}", "PHONE_NAME"))
    if business.address and business.city:
        keys.append((f"name_address:{normalize(business.normalized_name)}|{location}", "NAME_ADDRESS"))
    # Unidentified observations are intentionally not merged by a fuzzy name.
    if not keys:
        keys.append((f"observation:{business.run_id}:{business.id}", "OBSERVATION"))
    return [(hashlib.sha256(key.encode()).hexdigest(), kind) for key, kind in keys]


class ProspectRepository:
    def __init__(self, conn):
        self.conn = conn

    def observe(self, business, campaign_id=None, created_by=None):
        keys = identity_keys(business)
        if getattr(self.conn, "backend", None) == "postgres":
            # Sorted locks prevent deadlocks when two concurrent runs overlap.
            lock_ids=sorted(int(key[:15],16) for key,_ in keys)
            self.conn.execute("SELECT pg_advisory_xact_lock(lock_id) FROM (SELECT unnest(?::bigint[]) AS lock_id ORDER BY lock_id) locks", (lock_ids,))
        placeholders=','.join('?' for _ in keys)
        matched={row[0] for row in self.conn.execute(f"SELECT prospect_id FROM business_identities WHERE identity_key IN ({placeholders})", [key for key,_ in keys]).fetchall()}
        if len(matched) > 1:
            # Conflicting strong evidence needs review; never silently merge workflow.
            raise ValueError("Conflicting canonical identity evidence")
        prospect_id = next(iter(matched), None)
        timestamp = now()
        if not prospect_id:
            prospect_id = str(uuid.uuid4())
            first_seen=timestamp
            if business.created_at:
                try:
                    created=datetime.fromisoformat(business.created_at)
                    first_seen=(created if created.tzinfo else created.replace(tzinfo=timezone.utc)).isoformat()
                except ValueError:pass
            self.conn.execute("INSERT INTO prospects(id,first_seen_at,last_seen_at,first_campaign_id,updated_at,created_by) VALUES(?,?,?,?,?,?)", (prospect_id, first_seen, timestamp, campaign_id, timestamp, created_by))
        self.conn.executemany("INSERT INTO business_identities(identity_key,prospect_id,evidence_type) VALUES(?,?,?) ON CONFLICT(identity_key) DO NOTHING", [(key,prospect_id,kind) for key,kind in keys])
        if business.run_id is not None:
            inserted = self.conn.execute("INSERT INTO prospect_observations(prospect_id,run_id,business_id,observed_at) VALUES(?,?,?,?) ON CONFLICT(prospect_id,run_id) DO NOTHING", (prospect_id, business.run_id, business.id, timestamp)).rowcount
            if inserted:
                self.conn.execute("UPDATE prospects SET times_discovered=times_discovered+1,last_seen_at=? WHERE id=?", (timestamp, prospect_id))
        self.conn.execute("UPDATE businesses SET prospect_id=? WHERE id=?", (prospect_id, business.id))
        from app.database.phase4_schema import ready
        if ready(self.conn):
            from app.sales.service import activity
            activity(self.conn,prospect_id,created_by,'LEAD_DISCOVERED',{'business_id':business.id},'discovery-'+prospect_id)
        return prospect_id

    def user(self, email, display_name=None):
        from app.config.settings import get_settings
        if email not in get_settings().allowed_emails and get_settings().app_env != "test":
            raise ValueError("User is not allowlisted")
        self.conn.execute("INSERT INTO users(id,email,display_name,last_login) VALUES(?,?,?,?) ON CONFLICT(id) DO UPDATE SET last_login=excluded.last_login", (email, email, display_name or email.split("@")[0], now()))
        return email

    def workflow(self, prospect_id, actor, *, lead_status=None, assigned_to=...):
        if actor!='system':self.user(actor)
        previous=self.conn.execute('SELECT lead_status,assigned_to FROM prospects WHERE id=?',(prospect_id,)).fetchone()
        if lead_status is not None:
            self.conn.execute("UPDATE prospects SET lead_status=?,updated_by=?,updated_at=? WHERE id=?", (lead_status, actor, now(), prospect_id))
        if assigned_to is not ...:
            if assigned_to:
                self.user(assigned_to)
            self.conn.execute("UPDATE prospects SET assigned_to=?,updated_by=?,updated_at=? WHERE id=?", (assigned_to, actor, now(), prospect_id))
        from app.database.phase4_schema import ready
        if ready(self.conn):
            from app.sales.service import activity,status_event
            if lead_status is not None and previous and previous['lead_status']!=lead_status:status_event(self.conn,prospect_id,actor,lead_status,previous['lead_status'])
            if assigned_to is not ... and previous and previous['assigned_to']!=assigned_to:activity(self.conn,prospect_id,actor,'ASSIGNED',{'assigned_to':assigned_to})

    def add_note(self, prospect_id, actor, body):
        note_id = str(uuid.uuid4())
        self.user(actor)
        timestamp = now()
        self.conn.execute("INSERT INTO prospect_notes(id,prospect_id,body,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?)", (note_id, prospect_id, body, actor, timestamp, timestamp))
        from app.database.phase4_schema import ready
        if ready(self.conn):
            from app.sales.service import activity
            activity(self.conn,prospect_id,actor,'NOTE_ADDED',{'note_id':note_id},'note-'+note_id)
        return note_id

    def dossier(self, business_id):
        row = self.conn.execute("SELECT p.* FROM prospects p JOIN businesses b ON b.prospect_id=p.id WHERE b.id=?", (business_id,)).fetchone()
        if not row:
            return None
        result = dict(row)
        result["notes"] = [dict(r) for r in self.conn.execute("SELECT * FROM prospect_notes WHERE prospect_id=? ORDER BY created_at DESC LIMIT 100", (result["id"],)).fetchall()]
        score = self.conn.execute("SELECT * FROM opportunity_scores WHERE business_id=?", (business_id,)).fetchone()
        result["opportunity"] = dict(score) if score else None
        if result["opportunity"]:
            result["opportunity"]["evidence"] = json.loads(result["opportunity"].pop("evidence_json"))
        from app.database.phase36_schema import phase36_ready
        result['social_profiles'] = []
        result['intelligence'] = None
        if phase36_ready(self.conn):
            result['social_profiles'] = [dict(r) for r in self.conn.execute('SELECT platform,profile_url,handle,source_type,source_url,confidence,last_activity_at,activity_status,activity_source,activity_evidence_url,activity_checked_at,activity_reason FROM social_profiles WHERE prospect_id=? ORDER BY platform,profile_url', (result['id'],)).fetchall()]
            intelligence = self.conn.execute('SELECT * FROM business_intelligence WHERE business_id=?', (business_id,)).fetchone()
            result['intelligence'] = dict(intelligence) if intelligence else None
            if intelligence:
                for key in ('business_scale','scale_reason','scale_confidence'):result[key] = intelligence[key]
        return result
