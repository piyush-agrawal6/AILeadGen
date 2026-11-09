"""Emergency controls are authoritative across manual, bulk and scheduled paths."""
from fastapi import HTTPException

def require_unpaused(c,kind):
    row=c.execute('SELECT scan_paused,email_paused FROM automation_controls WHERE id=1').fetchone()
    if not row or row['scan_paused' if kind=='scan' else 'email_paused']:
        raise HTTPException(409,'Scanning is paused by the owner.' if kind=='scan' else 'Outreach is paused by the owner.')
