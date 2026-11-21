"""Authenticated marketing-plan handoff. Checkout and prices belong to Creem billing."""
from fastapi import HTTPException
from app.billing import commercial

def handoff(product,code):
    if product!='intent-radar':raise HTTPException(422,'Only Intent Radar plan selection is supported.')
    if code not in {p['code'] for p in commercial.catalog()['plans']}:raise HTTPException(422,'Choose a supported Intent Radar plan.')
    return {'product':'intent-radar','plan':code,'destination':'/billing?plan='+code,'checkout_enabled':False,'requires_authenticated_workspace':True,'commercial_price_approved':True}
