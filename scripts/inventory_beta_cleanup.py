"""Stage A only: inventory an exact restored backup and propose zero deletions.

No production connection, deletion command, email or payment operation exists in
this tool. Names and email domains cannot certify disposable customer data.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import psycopg
from psycopg import sql


def inventory(recovery_path, target, output):
    recovery = json.loads(Path(recovery_path).read_text())
    parsed = urlsplit(target)
    query = parse_qs(parsed.query)
    if parsed.hostname or query.get('host') != ['/private/tmp/planebyte-billing-pg18'] or parsed.path.lstrip('/') != recovery['local_restore_database']:
        raise ValueError('Only the verified local recovery database is permitted.')
    backup = Path(recovery['backup'])
    checksum = hashlib.sha256(backup.read_bytes()).hexdigest()
    if checksum != recovery['backup_sha256'] or not recovery['restored_exactly'] or recovery['row_loss']:
        raise ValueError('A verified exact backup and preserved history are required.')
    source = json.loads((Path(recovery_path).parent / 'source-fingerprints.json').read_text())
    with psycopg.connect(target, autocommit=True) as connection:
        connection.execute('BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY')
        connection.execute('SET LOCAL statement_timeout=30000')
        schema = connection.execute('SELECT MAX(version) FROM schema_migrations').fetchone()[0]
        tables = [r[0] for r in connection.execute("SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")]
        counts = {t: connection.execute(sql.SQL('SELECT COUNT(*) FROM {}').format(sql.Identifier(t))).fetchone()[0] for t in tables}
        workspaces = [dict(zip(('id', 'status', 'active_members'), r)) for r in connection.execute("SELECT o.id,o.status,COUNT(m.user_id) FROM organizations o LEFT JOIN organization_memberships m ON m.organization_id=o.id AND m.status='ACTIVE' GROUP BY o.id,o.status ORDER BY o.id")]
        users = [dict(zip(('id', 'role'), r)) for r in connection.execute('SELECT id,role FROM users ORDER BY id')]
        dependencies = [dict(zip(('table', 'references'), r)) for r in connection.execute("SELECT conrelid::regclass::text,confrelid::regclass::text FROM pg_constraint WHERE contype='f' AND connamespace='public'::regnamespace ORDER BY 1,2")]
        # The original billing_payments table is the retained Razorpay ledger;
        # it has no provider column. Preserve its classification explicitly.
        payments = [{'provider': 'razorpay', **dict(zip(('mode', 'status', 'records'), r))} for r in connection.execute('SELECT mode,status,COUNT(*) FROM billing_payments GROUP BY mode,status ORDER BY mode,status')]
        connection.execute('ROLLBACK')
    result = {
        'stage': 'A', 'production_written': False, 'cleanup_executed': False,
        'deletion_authorized': False, 'proposed_record_count': 0, 'deletions': [],
        'backup': str(backup), 'backup_sha256': checksum,
        'backup_bytes': backup.stat().st_size, 'source_schema': recovery['source_schema'],
        'restored_schema': schema, 'restore_verified': True,
        'source_tables': {t: {'count': v['count'], 'sha256': v['sha256'], 'action': 'PRESERVE'} for t, v in source.items()},
        'restored_table_counts': counts, 'foreign_key_dependencies': dependencies,
        'workspaces_for_owner_classification': [{**w, 'classification': 'UNVERIFIED — PRESERVE'} for w in workspaces],
        'accounts_for_owner_classification': [{**u, 'classification': 'UNVERIFIED — PRESERVE'} for u in users],
        'historical_payment_summary': payments,
        'protected_records': ['all Lead Engine and shared data', 'contacts, message and reply history', 'suppression and opt-out records', 'all original payment/refund provider and test/live classifications', 'audit logs and migration history', 'credentials references and integration ownership', 'all workspaces and accounts pending explicit owner classification'],
        'reason': 'No account or workspace has been owner-certified disposable. Test-like names and synthetic acceptance rows do not authorize deleting related customer or Lead Engine data.',
        'restore_instructions': 'Use the matching pg_restore binary against a NEW local PostgreSQL database. Compare every source-fingerprints.json table hash/count, then apply versioned migrations and verify the second run applies zero migrations. Never restore over production as an operational cleanup shortcut.',
    }
    destination = Path(output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as handle:
        json.dump(result, handle, indent=2)
    print(json.dumps({'status': 'PASS', 'stage': 'A', 'source_tables': len(source), 'workspace_count': len(workspaces), 'account_count': len(users), 'proposed_deletions': 0, 'production_written': False, 'manifest': str(destination)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--recovery-result', required=True)
    parser.add_argument('--local-database', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    inventory(args.recovery_result, args.local_database, args.output)
