"""Normalize optional JSON columns without treating missing source data as errors."""
import json

def optional_text(value):
    if not isinstance(value,str):return None
    text=value.strip()
    return text if text and text.casefold() not in ('nan','none','null','<na>','nat') else None

def source_metadata(taxonomy,socials):
    def decode(value,expected):
        if isinstance(value,expected):return value
        if not isinstance(value,str):return expected()
        try:parsed=json.loads(value)
        except (ValueError,TypeError):return expected()
        return parsed if isinstance(parsed,expected) else expected()
    tags=decode(taxonomy,dict)
    return json.dumps({**tags,'socials':[url for url in decode(socials,list) if isinstance(url,str)]})
