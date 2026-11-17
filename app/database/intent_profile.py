"""Independent, structure-only PostgreSQL lineage for the fresh Radar database.

The legacy 1..51 history remains available for the preserved Lead Engine source.
This lineage records only its own 1001+ migrations and never seeds a customer.
"""
import hashlib
import json
from pathlib import Path

PROFILE = 'intent-radar-v1'
ROOT = Path(__file__).with_name('intent_migrations')


def manifest():
    return json.loads((ROOT/'manifest.json').read_text())


def migrations():
    return [(int(p.name.split('_',1)[0]),p.name,p.read_text(),hashlib.sha256(p.read_bytes()).hexdigest())
            for p in sorted(ROOT.glob('[0-9]*_*.sql'))]


def _postgres(c):
    if getattr(c,'backend',None)!='postgres':
        raise RuntimeError('The clean Intent Radar profile requires PostgreSQL')
    from app.config.settings import get_settings
    if get_settings().lead_engine_available:
        raise RuntimeError('The clean Intent Radar schema cannot enable Lead Engine')


def _tables(c):
    return {r[0] for r in c.execute('SELECT tablename FROM pg_tables WHERE schemaname=?',(c.schema,)).fetchall()}


def verify(c,minimum_version=None):
    _postgres(c)
    expected=migrations();description=manifest()
    rows=c.execute('SELECT version,name,checksum FROM schema_migrations ORDER BY version').fetchall()
    if not rows or [(r['version'],r['name'],r['checksum']) for r in rows] != [(n,name,digest) for n,name,_,digest in expected[:len(rows)]]:
        raise RuntimeError('Intent Radar migration history or checksum does not match this release')
    actual=rows[-1]['version']
    if actual!=expected[-1][0]:
        description=description.get('previous_versions',{}).get(str(actual))
        if description is None:raise RuntimeError('Intent Radar schema version is not supported by this bridge release')
    if minimum_version and minimum_version>actual:
        raise RuntimeError('Intent Radar schema is older than the required version')
    row=c.execute('SELECT profile,source_baseline,structure_manifest_sha256 FROM intent_schema_metadata WHERE singleton=1').fetchone()
    if not row or row['profile']!=PROFILE or row['source_baseline']!=description['source_baseline'] or row['structure_manifest_sha256']!=description['structure_manifest_sha256']:
        raise RuntimeError('Intent Radar schema profile identity does not match')
    required=set(description['application_tables'])|{'schema_migrations','intent_schema_metadata'}
    if _tables(c)!=required:
        raise RuntimeError('Intent Radar schema table inventory does not match')
    return actual


def migrate(c):
    """Explicit atomic migration; reject an existing legacy or unrelated schema."""
    _postgres(c)
    tables=_tables(c)
    if tables:
        if 'intent_schema_metadata' not in tables:
            raise RuntimeError('Refusing to migrate an existing legacy or unrelated schema')
        if verify(c)==migrations()[-1][0]:
            c.commit()
            return 0
    try:
        c.execute('SELECT pg_advisory_xact_lock(691944317)')
        # Recheck after serialization: concurrent first-time operators must not
        # race table creation or seed a second migration history.
        applied=0
        if _tables(c):
            current=verify(c)
        else:
            current=0
            c.execute('''CREATE TABLE schema_migrations (
            version INTEGER PRIMARY KEY,name TEXT NOT NULL,checksum TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP::text))''')
        for number,name,sql,digest in migrations():
            if number<=current:continue
            # Static DDL is sent as one simple-protocol batch. Splitting on
            # semicolons would corrupt quoted SQL or comments and add hundreds
            # of remote round trips. The surrounding transaction stays atomic.
            with c.raw.cursor() as cursor:
                cursor.execute(sql.replace('__PLANEBYTE_SCHEMA__','"'+c.schema+'"'),prepare=False)
            c.execute('INSERT INTO schema_migrations(version,name,checksum) VALUES(?,?,?)',(number,name,digest))
            applied+=1
        verify(c,minimum_version=migrations()[-1][0])
        c.commit()
        return applied
    except BaseException:
        c.rollback()
        raise


def structure_fingerprints(c,tables=None):
    """Operator verification of columns, indexes and constraints; never row data."""
    tables=sorted(tables or manifest()['application_tables'])
    result={t:{'columns':[],'constraints':[],'indexes':[]} for t in tables}
    queries={
        'columns':'''SELECT t.relname,a.attname,a.attnum,format_type(a.atttypid,a.atttypmod) type,a.attnotnull,
            pg_get_expr(d.adbin,d.adrelid) default_sql FROM pg_attribute a JOIN pg_class t ON t.oid=a.attrelid
            JOIN pg_namespace n ON n.oid=t.relnamespace LEFT JOIN pg_attrdef d ON d.adrelid=t.oid AND d.adnum=a.attnum
            WHERE n.nspname=? AND t.relname=ANY(?) AND a.attnum>0 AND NOT a.attisdropped ORDER BY t.relname,a.attnum''',
        'constraints':'''SELECT t.relname,k.conname,k.contype,pg_get_constraintdef(k.oid) definition
            FROM pg_constraint k JOIN pg_class t ON t.oid=k.conrelid JOIN pg_namespace n ON n.oid=t.relnamespace
            WHERE n.nspname=? AND t.relname=ANY(?) ORDER BY t.relname,k.conname''',
        'indexes':'''SELECT t.relname,i.relname index_name,pg_get_indexdef(x.indexrelid) definition,x.indisvalid
            FROM pg_index x JOIN pg_class t ON t.oid=x.indrelid JOIN pg_class i ON i.oid=x.indexrelid
            JOIN pg_namespace n ON n.oid=t.relnamespace WHERE n.nspname=? AND t.relname=ANY(?) ORDER BY t.relname,i.relname'''}
    for kind,sql in queries.items():
        for row in c.execute(sql,(c.schema,tables)).fetchall():
            fields={k:(v.replace(c.schema+'.','__SCHEMA__.') if isinstance(v,str) else v) for k,v in dict(row).items() if k!='relname'}
            result[row['relname']][kind].append(fields)
    return {table:hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest() for table,value in result.items()}


def assert_fresh(c):
    """Gate the new destination before cutover: no customer or fake seeded rows."""
    verify(c)
    description=manifest()
    if structure_fingerprints(c)!=description['table_structure_sha256']:
        raise RuntimeError('Destination columns, indexes or constraints differ from the approved baseline')
    queries=['SELECT '+repr(t)+' AS table_name,COUNT(*) AS count FROM '+t for t in description['application_tables']]
    rows=c.execute(' UNION ALL '.join(queries)).fetchall()
    if any(r['count'] for r in rows):
        raise RuntimeError('The fresh destination contains unexpected application records')
    return {'profile':PROFILE,'schema_version':migrations()[-1][0],
            'application_tables':len(rows),'customer_and_application_records':0,
            'structure_verified':True,'excluded_legacy_tables':len(description['excluded_legacy_tables'])}
