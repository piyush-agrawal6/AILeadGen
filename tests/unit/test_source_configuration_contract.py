from app.config.settings import Settings

def test_existing_comma_sites_and_semicolon_hosts_preserve_all_entries():
    settings=Settings(intent_radar_stackexchange_sites='stackoverflow, serverfault;security,stackoverflow',intent_radar_approved_feed_hosts='meta.discourse.org; community.vercel.com')
    assert settings.intent_radar_stackexchange_sites=='stackoverflow;serverfault;security'
    assert settings.intent_radar_approved_feed_hosts=='meta.discourse.org;community.vercel.com'

def test_empty_source_configuration_stays_disabled():
    settings=Settings(intent_radar_stackexchange_sites='',intent_radar_approved_feed_hosts='')
    assert settings.intent_radar_stackexchange_sites==settings.intent_radar_approved_feed_hosts==''
