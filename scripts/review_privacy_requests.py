"""Internal case review. Defaults to read-only; contains no deletion operation."""
import argparse,json
from uuid import UUID
from app.config.settings import get_settings
from app.database.connection import db_session
from app.accounts.privacy import verify_closure

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operator',required=True)
    parser.add_argument('--record-verified-closure',type=UUID)
    parser.add_argument('--review-reference')
    args=parser.parse_args()
    if args.operator not in get_settings().allowed_emails:raise SystemExit('An authorized internal operator is required.')
    with db_session() as c:
        if args.record_verified_closure:
            if not args.review_reference:raise SystemExit('A scoped review reference is required; no closure was recorded.')
            result=verify_closure(c,str(args.record_verified_closure),args.operator,args.review_reference)
        else:
            result={'items':[dict(r) for r in c.execute("SELECT id,kind,status,created_at,ordinary_data_due_at,backup_target_at FROM account_privacy_requests WHERE status NOT IN ('COMPLETED','REJECTED') ORDER BY ordinary_data_due_at NULLS LAST,created_at LIMIT 100").fetchall()],'data_deleted':False}
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
