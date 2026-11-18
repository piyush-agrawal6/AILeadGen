import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from app.config.settings import get_settings
from app.integrations.crypto import seal,open_envelope

def test_source_cache_uses_owned_vault_without_relaxing_credential_limit(monkeypatch):
    monkeypatch.setattr(get_settings(),'heysow_integration_encryption_key',Fernet.generate_key().decode())
    context={'organization_id':'owned','connection_id':'cache-fingerprint','provider':'github','purpose':'SOURCE_CACHE'}
    value={'response':{'public':False,'body':'private source '*4000}}
    token=seal(value,**context)
    assert 'private source' not in token and open_envelope(token,**context)==value
    with pytest.raises(HTTPException):open_envelope(token,**{**context,'organization_id':'foreign'})
    with pytest.raises(HTTPException):seal(value,**{**context,'purpose':'CREDENTIALS'})
