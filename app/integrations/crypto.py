"""Server-only authenticated envelopes bind credentials to their exact owner."""
import json
from cryptography.fernet import Fernet,InvalidToken
from fastapi import HTTPException
from app.config.settings import get_settings


def cipher():
    value=get_settings().heysow_integration_encryption_key
    try:
        if not value:raise ValueError()
        return Fernet(value.encode('ascii'))
    except (ValueError,UnicodeError):
        raise HTTPException(503,'Workspace integrations need secure server configuration.') from None


def seal(value,*,organization_id,connection_id,provider,purpose):
    body=json.dumps({'version':1,'organization_id':organization_id,'connection_id':connection_id,'provider':provider,'purpose':purpose,'value':value},separators=(',',':')).encode()
    if len(body)>32_000:raise HTTPException(422,'Connection credentials exceed the supported size.')
    return cipher().encrypt(body).decode('ascii')


def open_envelope(token,*,organization_id,connection_id,provider,purpose):
    key=cipher()
    try:
        if not token or len(token)>50_000:raise ValueError()
        result=json.loads(key.decrypt(token.encode('ascii')))
        expected={'version':1,'organization_id':organization_id,'connection_id':connection_id,'provider':provider,'purpose':purpose}
        if not isinstance(result,dict) or {name:result.get(name) for name in expected}!=expected or not isinstance(result.get('value'),dict):raise ValueError()
        return result['value']
    except (InvalidToken,ValueError,TypeError,UnicodeError):
        raise HTTPException(409,'This workspace connection needs to be reconnected.') from None
