"""Readiness probes must tolerate poolers and never expose connection secrets."""
import json
from unittest.mock import Mock
from scripts.inspect_beta_runtime import database

def test_metadata_probe_enters_readonly_transaction_after_standard_connect(monkeypatch):
    import psycopg
    connection=Mock();connection.__enter__=Mock(return_value=connection);connection.__exit__=Mock(return_value=False)
    def execute(statement):
        cursor=Mock()
        cursor.fetchone.return_value={'SHOW transaction_read_only':('on',),'SHOW server_version':('18.6',),"SELECT to_regclass('schema_migrations')":(None,)}.get(statement)
        cursor.fetchall.return_value=[]
        return cursor
    connection.execute.side_effect=execute;connect=Mock(return_value=connection);monkeypatch.setattr(psycopg,'connect',connect)
    result=database('postgresql://synthetic-private-credential')
    assert result['connected'] and result['read_only'] and result['version']=='18.6'
    assert 'options' not in connect.call_args.kwargs
    assert [item.args[0] for item in connection.execute.call_args_list[:2]]==['BEGIN READ ONLY','SET LOCAL statement_timeout=5000']

def test_metadata_failure_omits_credentials_and_driver_error_body(monkeypatch):
    import psycopg
    secret='synthetic-private-password';monkeypatch.setattr(psycopg,'connect',Mock(side_effect=RuntimeError(secret)))
    result=database('postgresql://'+secret)
    assert result['connected'] is False and result['error_type']=='RuntimeError'
    assert secret not in json.dumps(result)

def test_source_example_does_not_embed_stack_apps_credential():
    from pathlib import Path
    from dotenv import dotenv_values
    values=dotenv_values(Path(__file__).resolve().parents[2]/'.env.example',interpolate=False)
    assert not values.get('INTENT_RADAR_STACKEXCHANGE_KEY')
