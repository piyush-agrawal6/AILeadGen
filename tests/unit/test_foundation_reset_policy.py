"""Operational reset is explicitly scoped; consent and configuration survive."""
import importlib.util,sys
from pathlib import Path

def test_clean_start_policy_keeps_security_and_suppression(monkeypatch):
    monkeypatch.syspath_prepend(str(Path('scripts').resolve()))
    monkeypatch.setenv('DATABASE_BACKEND','sqlite')
    spec=importlib.util.spec_from_file_location('foundation_reset_policy','scripts/foundation_clean_start.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert module.PRESERVE.isdisjoint(module.OPERATIONAL)
    for table in ('schema_migrations','users','shared_settings','email_accounts','scan_markets','email_address_suppressions','account_roles','audit_log','recovery_checkpoints'):assert table in module.PRESERVE
    for table in ('prospects','businesses','email_messages','email_threads','scan_campaigns','automation_schedules','client_reports','email_tracking_tokens'):assert table in module.OPERATIONAL
