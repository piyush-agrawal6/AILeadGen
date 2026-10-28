"""Small PostgreSQL DB-API adapter retaining the existing parameterized repositories."""
import re
import psycopg
from urllib.parse import urlsplit,urlunsplit


def session_url(url):
    """Neon transaction pooling cannot retain a worker's session advisory lock."""
    parts=urlsplit(url);host=parts.hostname or ''
    if host.endswith('.neon.tech') and '-pooler.' in host:
        authority=parts.netloc.replace(host,host.replace('-pooler.','.',1))
        return urlunsplit(parts._replace(netloc=authority))
    return url


class Record(dict):
    """Mapping rows also support the legacy aggregate row[0] convention."""
    def __init__(self,items,values):
        super().__init__(items)
        self._positional=tuple(values)

    def __getitem__(self, key):
        return self._positional[key] if isinstance(key, int) else super().__getitem__(key)


def record_factory(cursor):
    names = [column.name for column in (cursor.description or [])]
    return lambda values: Record(zip(names, values),values)


class Cursor:
    def __init__(self, cursor, lastrowid=None):
        self.cursor = cursor
        self.lastrowid = lastrowid

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def fetchone(self):
        return self.cursor.fetchone()

    def fetchall(self):
        return self.cursor.fetchall()


ID_TABLES = {"businesses", "website_profiles", "contacts", "lighthouse_results", "findings", "pipeline_runs", "pipeline_run_events", "scan_campaigns", "prospects", "prospect_notes", "users"}


class PostgresConnection:
    backend = "postgres"

    def __init__(self, url, *, schema=None, session_bound=False):
        self.schema=schema or 'public'
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", self.schema):
            raise ValueError("Invalid database schema")
        self.raw = psycopg.connect(session_url(url) if session_bound else url, row_factory=record_factory, connect_timeout=15)

    def _prepare_transaction(self):
        if self.raw.info.transaction_status == psycopg.pq.TransactionStatus.IDLE:
            # SET LOCAL is reapplied after every commit, even when a transaction
            # pooler chooses a different backend. Schema names are validated.
            self.raw.execute(f"SET LOCAL search_path TO {self.schema}; SET LOCAL TIME ZONE 'UTC'; SET LOCAL statement_timeout = '30s'")

    def execute(self, statement, parameters=()):
        self._prepare_transaction()
        # SQL is application-owned; parameters always remain driver-bound.
        statement = statement.replace("?", "%s")
        insert = re.match(r"\s*INSERT\s+INTO\s+([a-z_]+)", statement, re.I)
        returning = insert and insert.group(1).lower() in ID_TABLES and "RETURNING" not in statement.upper()
        if returning:
            statement = statement.rstrip().rstrip(";") + " RETURNING id"
        cursor = self.raw.execute(statement, parameters)
        last_id = None
        if returning:
            row = cursor.fetchone()
            last_id = row[0] if row else None
        return Cursor(cursor, last_id)

    def executescript(self, script):
        for statement in script.split(";"):
            if statement.strip():
                self.execute(statement)

    def executemany(self,statement,parameters):
        self._prepare_transaction()
        cursor=self.raw.cursor()
        cursor.executemany(statement.replace("?","%s"),parameters)
        return Cursor(cursor)

    def commit(self):
        self.raw.commit()

    def rollback(self):
        self.raw.rollback()

    def close(self):
        self.raw.close()
