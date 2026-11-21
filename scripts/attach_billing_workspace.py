"""Verify both owners and all financial-history guards. Dry run unless --apply is given."""
import argparse,os
from uuid import UUID
from app.billing.accounts import attach_empty
from app.database.postgres import PostgresConnection
from app.database.intent_profile import verify

def main():
    p=argparse.ArgumentParser();p.add_argument('--account',required=True,type=UUID);p.add_argument('--workspace',required=True,type=UUID);p.add_argument('--owner',required=True);p.add_argument('--reason',required=True);p.add_argument('--apply',action='store_true');a=p.parse_args();c=PostgresConnection(os.environ['PLANEBYTE_ADMIN_DATABASE_URL'],schema='public')
    try:
        verify(c,minimum_version=1016);user,ok=c.raw.execute('SELECT session_user,session_user=pg_get_userbyid(datdba) FROM pg_database WHERE datname=current_database()').fetchone()._positional
        if not ok:raise PermissionError('Database owner required')
        changed=attach_empty(c,str(a.account),str(a.workspace),a.owner,'database-owner:'+user,a.reason)
        if a.apply:c.commit()
        else:c.rollback()
        print('Attached' if a.apply and changed else 'Would attach' if changed else 'Already attached')
    finally:c.close()

if __name__=='__main__':main()
