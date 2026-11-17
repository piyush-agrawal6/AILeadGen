"""Small PostgreSQL DB-API adapter retaining the existing parameterized repositories."""
import re,os,threading,time
from contextlib import nullcontext
import psycopg
from urllib.parse import urlsplit,urlunsplit

_pools={}
_pool_lock=threading.Lock()

def connection_pool(url):
    from psycopg_pool import ConnectionPool
    with _pool_lock:
        if url not in _pools:
            pool=ConnectionPool(url,min_size=0,max_size=4,max_waiting=32,timeout=8,
                                max_idle=30,max_lifetime=600,open=False,
                                kwargs={'row_factory':record_factory,'connect_timeout':10,'prepare_threshold':None,'application_name':'planebyte-api'})
            pool.open();_pools[url]=pool
        return _pools[url]

def close_pools():
    with _pool_lock:
        for pool in _pools.values():pool.close()
        _pools.clear()


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
        self.pool=None
        if not session_bound and schema is None and os.environ.get('LEADENGINE_ROLE')!='worker' and os.environ.get('APP_ENV')=='production':
            self.pool=connection_pool(url);self.raw=self.pool.getconn()
        else:
            self.raw = psycopg.connect(session_url(url) if session_bound else url, row_factory=record_factory, connect_timeout=15,application_name='planebyte-worker' if os.environ.get('LEADENGINE_ROLE')=='worker' else 'planebyte-isolated')
        self.closed=False

    def _prepare_transaction(self):
        if self.raw.info.transaction_status == psycopg.pq.TransactionStatus.IDLE:
            # SET LOCAL is reapplied after every commit, even when a transaction
            # pooler chooses a different backend. Schema names are validated.
            started=time.monotonic()
            try:self.raw.execute("SELECT set_config('search_path',%s,true),set_config('TimeZone','UTC',true),set_config('statement_timeout','30s',true)",(self.schema,))
            finally:
                from app.platform.request_metrics import database
                database(time.monotonic()-started)

    def execute(self, statement, parameters=()):
        # SQL is application-owned; parameters always remain driver-bound.
        statement = statement.replace("?", "%s")
        insert = re.match(r"\s*INSERT\s+INTO\s+([a-z_]+)", statement, re.I)
        returning = insert and insert.group(1).lower() in ID_TABLES and "RETURNING" not in statement.upper()
        if returning:
            statement = statement.rstrip().rstrip(";") + " RETURNING id"
        started=time.monotonic()
        try:
            # The setup and first statement share one network flush. SET LOCAL
            # remains transaction-scoped and is reapplied after every commit;
            # transaction poolers cannot leak another workspace's search_path.
            fresh=self.raw.info.transaction_status == psycopg.pq.TransactionStatus.IDLE
            with self.raw.pipeline() if fresh else nullcontext():
                self._prepare_transaction()
                cursor = self.raw.execute(statement, parameters)
        finally:
            from app.platform.request_metrics import database
            database(time.monotonic()-started)
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

    def insert_many_ids(self,statement,parameters):
        """Pipeline inserts while preserving repository-assigned result IDs."""
        self._prepare_transaction()
        with self.raw.cursor() as cursor:
            cursor.executemany(statement.replace('?','%s')+' RETURNING id',parameters,returning=True)
            result=[]
            if parameters:
                while True:
                    result.append(cursor.fetchone()[0])
                    if not cursor.nextset():break
            return result

    def rollback(self):
        self.raw.rollback()

    def close(self):
        if self.closed:return
        self.closed=True
        if self.pool:
            try:self.raw.rollback()
            finally:self.pool.putconn(self.raw)
        else:self.raw.close()
