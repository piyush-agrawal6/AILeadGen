import pytest
from app.intent_radar.connectors import parse_feed
CONFIG={'id':'approved','name':'Publisher','family':'rss','endpoint':'https://example.com/releases/feed','attribution':'Publisher','policy_reference':'Reviewed source license','retention_days':7}

def test_atom_nested_authors_categories_relative_xhtml_and_update_identity():
    body=b'''<feed xmlns="http://www.w3.org/2005/Atom" xml:base="https://example.com/releases/"><link rel="self" href="feed"/><entry><id>urn:release:1</id><title>Release one</title><link rel="self" href="feed/1"/><link rel="alternate" href="one#changes"/><author><name>Publisher Name</name></author><category term="software"/><category term="AI"/><published>2026-11-17T10:00:00Z</published><updated>2026-11-18T10:00:00Z</updated><content type="xhtml"><div xmlns="http://www.w3.org/1999/xhtml"><p>Supported <b>release notes</b>.</p><script>evil()</script></div></content></entry></feed>'''
    first=parse_feed(body,CONFIG)[0];changed=parse_feed(body.replace(b'Supported',b'Updated'),CONFIG)[0]
    assert first['source_url']=='https://example.com/releases/one#changes'
    assert first['provenance']['feed_authors']==['Publisher Name']
    assert first['provenance']['categories']==['software','AI']
    assert first['provenance']['updated_at'].startswith('2026-11-18')
    assert first['source_record_id']==changed['source_record_id'] and first['content_fingerprint']!=changed['content_fingerprint']
    assert 'release notes' in first['excerpt'] and 'evil()' not in first['excerpt']

def test_http_original_links_fragments_and_explicit_tombstones_are_preserved():
    body=b'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:at="http://purl.org/atompub/tombstones/1.0"><entry><id>one</id><title>Research</title><link href="http://arxiv.org/abs/1?utm_source=feed#abstract"/><updated>2026-11-18T10:00:00Z</updated></entry><at:deleted-entry ref="removed" when="2026-11-18T10:00:00Z"/></feed>'
    items=parse_feed(body,CONFIG)
    assert items[0]['source_url']=='http://arxiv.org/abs/1#abstract'
    assert items[0]['provenance']['observed_time_basis']=='updated'
    assert items[1]['removed'] is True and items[1]['source']=='RSS / Atom'

@pytest.mark.parametrize('body',[b'<html><entry/></html>','<!DOCTYPE rss [<!ENTITY x "value">]><rss/>'.encode('utf-16'),b'<rss>'+b'<x>'*40+b'</x>'*40+b'</rss>'])
def test_unsafe_or_non_feed_xml_is_rejected(body):
    with pytest.raises(ValueError):parse_feed(body,CONFIG)

def test_legitimately_empty_atom_is_successful():
    assert parse_feed(b'<feed xmlns="http://www.w3.org/2005/Atom"/>',CONFIG)==[]
