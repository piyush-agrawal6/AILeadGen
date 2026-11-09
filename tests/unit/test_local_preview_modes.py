"""Live-feature preview opt-in never changes .env, shares secrets with UI or starts production jobs."""
import os
import runpy
import sys
from pathlib import Path
import pytest
import dotenv


@pytest.mark.parametrize('mode,option',[('backend','--all-features'),('frontend','--all-features'),('backend','--icp-ai'),('backend','')])
def test_preview_modes_preserve_local_boundaries_and_owner_choices(monkeypatch,mode,option):
    script=Path(__file__).resolve().parents[2]/'scripts/local_preview.py';captured={}
    monkeypatch.setattr(dotenv,'dotenv_values',lambda path:{'AUTH_SECRET':'fixture-auth-only','FIRECRAWL_API_KEY':'fixture-provider-only','HEYSOW_INTEGRATION_ENCRYPTION_KEY':'fixture-envelope-only','UPSTASH_REDIS_REST_TOKEN':'fixture-cache-only','VERTEX_AI_MODEL':'gemini-3.6-flash'})
    monkeypatch.setattr(sys,'argv',[str(script),mode]+([option] if option else []));monkeypatch.setattr(os,'chdir',lambda path:None)
    class Started(Exception):pass
    def launch(executable,args,env):captured.update(env);raise Started()
    monkeypatch.setattr(os,'execve',launch);monkeypatch.setattr(os,'execvpe',launch)
    with pytest.raises(Started):runpy.run_path(str(script),run_name='__main__')
    assert captured['APP_ENV']=='development' and captured['DATABASE_BACKEND']=='sqlite'
    assert captured['DATABASE_URL']=='' and captured['STORAGE_BACKEND']=='local'
    assert captured['SCAN_EXECUTOR']=='local' and captured['AUTH_DISABLED_LOCAL']=='false'
    assert captured['EMAIL_SENDING_ENABLED']=='false' and captured['AUTO_EMAIL_ENABLED']=='false'
    assert captured['HEYSOW_INTERNAL_EXPERIMENTS_ENABLED']=='false' and captured['GEMINI_API_ENABLED']=='false'
    if option=='--all-features':
        for key in ('HEYSOW_ICP_AI_ENABLED','HEYSOW_LEAD_ASSISTANT_ENABLED','HEYSOW_CUSTOMER_INTEGRATIONS_ENABLED','HEYSOW_DEVELOPER_API_ENABLED','HEYSOW_MCP_ENABLED','ENABLE_LEAD_IMPORT','ENABLE_FIRECRAWL_ACQUISITION','AUTO_SCAN_ENABLED'):assert captured[key]=='true'
        if mode=='backend':assert captured['FIRECRAWL_API_KEY']=='fixture-provider-only'
        else:assert captured['FIRECRAWL_API_KEY']=='' and 'HEYSOW_INTEGRATION_ENCRYPTION_KEY' not in captured
    elif option=='--icp-ai':assert captured['HEYSOW_ICP_AI_ENABLED']=='true' and captured['ENABLE_FIRECRAWL_ACQUISITION']=='false'
    else:assert captured['HEYSOW_ICP_AI_ENABLED']=='false' and captured['VERTEX_AI_ENABLED']=='false'
