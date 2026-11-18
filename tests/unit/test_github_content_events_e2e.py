"""End-to-end verification of all 6 subscribed GitHub content webhook events."""
import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone

import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException
from pydantic import SecretStr

from app.config.settings import get_settings
from app.intent_radar import models, service
from app.intent_radar.github_source import ingest_webhook
from app.platform.context import workspace_scope
from test_intent_radar import radar, owned  # noqa: F401 - pytest fixtures


def _sign(body: bytes, secret: str) -> str:
    return 'sha256=' + hmac.new(secret.encode('utf-8'), body, hashlib.sha256).hexdigest()


def _setup_github_workspace(c, org, monkeypatch, *, inst_id='182630541', repos_json='[]'):
    s = get_settings()
    secret = 'whsec_test_all_6_events_secret'
    monkeypatch.setattr(s, 'intent_radar_sources_v2_enabled', True)
    monkeypatch.setattr(s, 'heysow_integration_encryption_key', Fernet.generate_key().decode())
    monkeypatch.setattr(s, 'intent_radar_github_enabled', True)
    monkeypatch.setattr(s, 'intent_radar_github_webhooks_enabled', True)
    monkeypatch.setattr(s, 'github_app_webhook_secret', SecretStr(secret))
    monkeypatch.setattr(s, 'github_app_id', '5786999')
    monkeypatch.setattr(s, 'github_app_private_key', SecretStr('fake-pem'))
    ts = datetime.now(timezone.utc).isoformat()
    c.execute(
        "INSERT INTO intent_github_connections(id,organization_id,owner_user_id,installation_id,account_login,account_type,status,permissions_json,repositories_json,revision,created_at,updated_at) "
        "VALUES(?,?,?,?,?,'Organization','CONNECTED','{}',?,1,?,?)",
        (str(uuid.uuid4()), org, 'controlled@example.test', inst_id, 'planebytelabs', repos_json, ts, ts),
    )
    service.save_monitor(
        c,
        models.Monitor(
            name='GitHub All-Events Monitor',
            status='Active',
            configuration=models.Search(
                keywords=['crm', 'automation', 'webhook'],
                sources=['github'],
                github_repos=['planebytelabs/intent-sandbox'],
            ),
        ),
    )
    c.commit()
    return secret, ts


def test_all_six_github_content_events_ingest_dedupe_and_surface_in_signals(radar, monkeypatch):
    c, _, org_a, org_b = radar
    with workspace_scope(c, 'controlled@example.test', org_a):
        secret, ts = _setup_github_workspace(c, org_a, monkeypatch)
        repo = {'id': 501, 'full_name': 'planebytelabs/intent-sandbox', 'private': False}
        inst = {'id': 182630541}

        events = [
            (
                'issues',
                {
                    'action': 'opened',
                    'installation': inst,
                    'repository': repo,
                    'issue': {
                        'id': 9101,
                        'number': 1,
                        'html_url': 'https://github.com/planebytelabs/intent-sandbox/issues/1',
                        'title': 'Looking for a CRM tool with webhook automation',
                        'body': 'We are evaluating alternatives to replace our legacy CRM automation.',
                        'created_at': ts,
                        'user': {'login': 'buyer_alice', 'html_url': 'https://github.com/buyer_alice'},
                        'labels': [{'name': 'evaluation'}],
                    },
                },
                'issue:9101',
                'issue',
            ),
            (
                'issue_comment',
                {
                    'action': 'created',
                    'installation': inst,
                    'repository': repo,
                    'issue': {'id': 9101, 'number': 1, 'title': 'CRM evaluation thread'},
                    'comment': {
                        'id': 9202,
                        'html_url': 'https://github.com/planebytelabs/intent-sandbox/issues/1#issuecomment-9202',
                        'body': 'Can anyone recommend a CRM automation platform that integrates cleanly?',
                        'created_at': ts,
                        'user': {'login': 'ops_bob', 'html_url': 'https://github.com/ops_bob'},
                    },
                },
                'issue_comment:9202',
                'comment',
            ),
            (
                'discussion',
                {
                    'action': 'created',
                    'installation': inst,
                    'repository': repo,
                    'discussion': {
                        'id': 9303,
                        'html_url': 'https://github.com/planebytelabs/intent-sandbox/discussions/3',
                        'title': 'Comparing CRM automation vendors for B2B teams',
                        'body': 'We are comparing CRM platforms and seeking recommendations for workflow automation.',
                        'created_at': ts,
                        'user': {'login': 'lead_carol', 'html_url': 'https://github.com/lead_carol'},
                    },
                },
                'discussion:9303',
                'discussion',
            ),
            (
                'discussion_comment',
                {
                    'action': 'created',
                    'installation': inst,
                    'repository': repo,
                    'discussion': {'id': 9303, 'title': 'Comparing CRM automation vendors'},
                    'comment': {
                        'id': 9404,
                        'html_url': 'https://github.com/planebytelabs/intent-sandbox/discussions/3#discussioncomment-9404',
                        'body': 'We need a CRM replacement because our webhook sync is failing.',
                        'created_at': ts,
                        'user': {'login': 'eng_dave', 'html_url': 'https://github.com/eng_dave'},
                    },
                },
                'discussion_comment:9404',
                'comment',
            ),
            (
                'release',
                {
                    'action': 'published',
                    'installation': inst,
                    'repository': repo,
                    'release': {
                        'id': 9505,
                        'html_url': 'https://github.com/planebytelabs/intent-sandbox/releases/tag/v2.0.0',
                        'name': 'v2.0.0 Webhook Automation Engine',
                        'tag_name': 'v2.0.0',
                        'body': 'New release improving CRM webhook throughput and reliability.',
                        'published_at': ts,
                        'author': {'login': 'release_bot', 'html_url': 'https://github.com/release_bot'},
                    },
                },
                'release:9505',
                'release',
            ),
            (
                'pull_request',
                {
                    'action': 'opened',
                    'installation': inst,
                    'repository': repo,
                    'pull_request': {
                        'id': 9606,
                        'html_url': 'https://github.com/planebytelabs/intent-sandbox/pull/42',
                        'title': 'Add CRM webhook automation connector',
                        'body': 'Feature request: please add CRM webhook automation sync support.',
                        'created_at': ts,
                        'user': {'login': 'contrib_eve', 'html_url': 'https://github.com/contrib_eve'},
                    },
                },
                'pull_request:9606',
                'pull_request',
            ),
        ]

        for idx, (event_type, payload, expected_rec_id, expected_kind) in enumerate(events):
            raw = json.dumps(payload).encode('utf-8')
            sig = _sign(raw, secret)
            delivery_id = f'deliv-six-{idx}-{event_type}'

            # Invalid signature must always fail 401
            with pytest.raises(HTTPException) as bad:
                ingest_webhook(c, raw_body=raw, delivery_id=delivery_id + '-bad', event_type=event_type, signature='sha256=bad')
            assert bad.value.status_code == 401

            # First valid delivery succeeds
            res = ingest_webhook(c, raw_body=raw, delivery_id=delivery_id, event_type=event_type, signature=sig)
            assert res['status'] == 'COMPLETE'

            # Duplicate delivery is cleanly deduplicated
            dup = ingest_webhook(c, raw_body=raw, delivery_id=delivery_id, event_type=event_type, signature=sig)
            assert dup['status'] == 'DUPLICATE'

        listed = service.listing(c, 'signals', source='GitHub', page_size=50)
        assert listed['total'] == 6
        by_record = {item['source_record_id']: item for item in listed['items']}
        for _, _, expected_rec_id, expected_kind in events:
            assert expected_rec_id in by_record
            sig_item = by_record[expected_rec_id]
            prov = sig_item['evidence']['provenance']
            assert prov['fetch_method'] == 'github_webhook'
            assert prov['content_kind'] == expected_kind
            assert prov['repo'] == 'planebytelabs/intent-sandbox'
            # Never expose internal installation_id or organization_id in customer-visible evidence/provenance
            ev_str = json.dumps(sig_item['evidence'])
            assert '182630541' not in ev_str
            assert org_a not in ev_str

        # Release MUST be Market / technology intelligence and NEVER in high_intent view
        release_sig = by_record['release:9505']
        assert release_sig['category'] == 'Market / technology intelligence'
        high_intent = service.listing(c, 'signals', view='high_intent', page_size=50)
        high_ids = {s['source_record_id'] for s in high_intent['items']}
        assert 'release:9505' not in high_ids
        assert 'issue:9101' in high_ids

        # Noisy lifecycle actions (deleted / closed / labeled / synchronize) must be IGNORED
        for bad_event, bad_action, extra in [
            ('issues', 'deleted', {'issue': {'id': 9901, 'html_url': 'https://github.com/planebytelabs/intent-sandbox/issues/99', 'title': 'CRM alternative', 'body': 'Looking for CRM', 'created_at': ts}}),
            ('issues', 'labeled', {'issue': {'id': 9902, 'html_url': 'https://github.com/planebytelabs/intent-sandbox/issues/100', 'title': 'CRM alternative', 'body': 'Looking for CRM', 'created_at': ts}}),
            ('pull_request', 'synchronize', {'pull_request': {'id': 9903, 'html_url': 'https://github.com/planebytelabs/intent-sandbox/pull/101', 'title': 'CRM automation', 'body': 'Looking for CRM', 'created_at': ts}}),
            ('release', 'unpublished', {'release': {'id': 9904, 'html_url': 'https://github.com/planebytelabs/intent-sandbox/releases/tag/v0.1', 'name': 'CRM release', 'body': 'CRM', 'published_at': ts}}),
        ]:
            raw = json.dumps({'action': bad_action, 'installation': inst, 'repository': repo, **extra}).encode('utf-8')
            res = ingest_webhook(c, raw_body=raw, delivery_id=f'deliv-ignore-{bad_event}-{bad_action}', event_type=bad_event, signature=_sign(raw, secret))
            assert res['status'] == 'IGNORED'

        assert service.listing(c, 'signals', source='GitHub', page_size=50)['total'] == 6

    # Tenant isolation: Organization B (even with Intent Radar enabled) must NEVER see Organization A's webhook signals
    c.execute("UPDATE organization_products SET enabled=1 WHERE organization_id=? AND product='INTENT_RADAR'", (org_b,))
    c.commit()
    with workspace_scope(c, 'foreign@example.test', org_b):
        other_list = service.listing(c, 'signals', source='GitHub', page_size=50)
        assert other_list['total'] == 0
        assert other_list['items'] == []
