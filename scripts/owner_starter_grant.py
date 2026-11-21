"""Database-owner-only operator command. No HTTP endpoint, cloud change, or automatic renewal."""
import argparse,os
from datetime import datetime
from uuid import UUID
from app.database.postgres import PostgresConnection
from app.database.intent_profile import verify
from app.billing.owner_starter import record

def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=('issue','revoke'));p.add_argument('--workspace',required=True,type=UUID);p.add_argument('--grant-id',required=True,type=UUID);p.add_argument('--reason',required=True);p.add_argument('--expires');args=p.parse_args()
    expires=datetime.fromisoformat(args.expires) if args.expires else None
    if args.action=='issue' and (not expires or expires.tzinfo is None):p.error('A timezone-qualified expiry is required')
    c=PostgresConnection(os.environ['PLANEBYTE_ADMIN_DATABASE_URL'],schema='public')
    try:
        verify(c,minimum_version=1012)
        identity=c.execute('SELECT session_user,(session_user=pg_get_userbyid(datdba)) AS permitted FROM pg_database WHERE datname=current_database()').fetchone()
        if not identity or not identity['permitted']:raise PermissionError('The database owner is required')
        record(c,str(args.workspace),str(args.grant_id),end=int(expires.timestamp()) if expires else 0,reason=args.reason,administrator='database-owner:'+identity[0],revoke=args.action=='revoke');c.commit()
    finally:c.close()
if __name__=='__main__':main()
