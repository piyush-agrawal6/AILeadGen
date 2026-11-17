"""OWASP scrypt profile with bounded process memory and constant-time comparison.

No password logging, reversible password storage or client-side hashing contract.
"""
import base64
import hashlib
import hmac
import secrets
import threading
from fastapi import HTTPException

N,R,P=2**17,8,1
_slots=threading.BoundedSemaphore(2)
_COMMON=frozenset(('passwordpassword','password123456789','123456789012345','qwertyuiopasdfgh','letmeinletmeinletmein','correcthorsebatterystaple'))

def validate(value):
    if not isinstance(value,str) or not 15<=len(value)<=128 or len(value.encode('utf-8'))>512:
        raise ValueError('Use a password of 15 to 128 characters.')
    if value.casefold() in _COMMON or len(set(value))<5:
        raise ValueError('Choose a less predictable password or passphrase.')
    return value

def _derive(password,salt):
    if not _slots.acquire(blocking=False):raise HTTPException(429,'Sign-in capacity is temporarily busy. Retry shortly.')
    try:return hashlib.scrypt(password.encode('utf-8'),salt=salt,n=N,r=R,p=P,maxmem=256*1024*1024,dklen=32)
    finally:_slots.release()

def hash_password(value):
    validate(value);salt=secrets.token_bytes(16);derived=_derive(value,salt)
    return '$'.join(('scrypt','1',str(N),str(R),str(P),base64.urlsafe_b64encode(salt).decode(),base64.urlsafe_b64encode(derived).decode()))

def verify(value,encoded):
    # Missing accounts do comparable bounded KDF work without manufacturing a
    # persisted account, OTP or successful authentication result.
    if not isinstance(value,str) or len(value)>128 or len(value.encode('utf-8'))>512:return False
    if not encoded:
        _derive(value,b'planebyte-no-user');return False
    try:
        kind,version,n,r,p,salt,digest=encoded.split('$')
        if (kind,version,int(n),int(r),int(p))!=('scrypt','1',N,R,P):return False
        salt=base64.b64decode(salt,altchars=b'-_',validate=True);expected=base64.b64decode(digest,altchars=b'-_',validate=True)
        if len(salt)!=16 or len(expected)!=32:return False
    except (ValueError,TypeError):return False
    return hmac.compare_digest(_derive(value,salt),expected)
