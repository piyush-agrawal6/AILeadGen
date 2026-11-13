from pathlib import Path
import pytest
from scripts import deploy_beta_backend as release

def test_release_enables_only_approved_owner_without_activating_sends():
    assert release.FLAGS['ALLOWED_USER_EMAILS']=='planebyte@gmail.com'
    for flag in ('HEYSOW_PUBLIC_REGISTRATION_ENABLED','HEYSOW_INVITED_REGISTRATION_ENABLED','HEYSOW_CUSTOMER_ACCESS_ENABLED','AUTO_SCAN_ENABLED','AUTO_EMAIL_ENABLED','EMAIL_SENDING_ENABLED','HEYSOW_CUSTOMER_MAIL_SENDING_ENABLED','HEYSOW_INTERNAL_EXPERIMENTS_ENABLED'):
        assert release.FLAGS[flag]=='false'
    assert release.FLAGS['INTENT_RADAR_STAGE']=='Beta'
    assert release.FLAGS['MCP_ALLOWED_HOSTS']=='leadengine-api-befca7xg4a-el.a.run.app'

def test_failed_critical_suite_blocks_all_cloud_and_database_mutation(tmp_path,monkeypatch):
    monkeypatch.setattr(release,'EVIDENCE',tmp_path)
    (tmp_path/'backend-locked-pg18-final.xml').write_text('<testsuites><testsuite tests="1" failures="1" errors="0"/></testsuites>')
    monkeypatch.setattr(release,'command',lambda *a,**k:pytest.fail('Cloud mutation before gate'))
    monkeypatch.setattr(release,'PostgresConnection',lambda *a,**k:pytest.fail('DB access before gate'))
    with pytest.raises(RuntimeError,match='regression gate'):release.release()

def test_failed_restore_blocks_release_even_when_tests_pass(tmp_path,monkeypatch):
    monkeypatch.setattr(release,'EVIDENCE',tmp_path)
    (tmp_path/'backend-locked-pg18-final.xml').write_text('<testsuites><testsuite tests="1" failures="0" errors="0"/></testsuites>')
    (tmp_path/'recovery-history-final.json').write_text('{"original_columns_preserved":false}')
    monkeypatch.setattr(release,'command',lambda *a,**k:pytest.fail('Cloud mutation before recovery gate'))
    with pytest.raises(RuntimeError,match='Recovery preservation'):release.release()
