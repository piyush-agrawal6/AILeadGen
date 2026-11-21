"""Customer access/usage overview; sandbox fixtures stay behind existing billing gates."""
import json
from datetime import datetime,timedelta,timezone
from fastapi import HTTPException
from app.platform.context import current
from app.api.organization import membership_role,products
from app.config.settings import get_settings
from app.database.prospects import now

def overview(c):
    ctx=current();role=membership_role(c,ctx.actor,ctx.organization_id)
    if not role:raise HTTPException(403,'Active workspace membership required.')
    org=ctx.organization_id;s=get_settings();today=now()[:10]
    reset=(datetime.now(timezone.utc).replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=1)).isoformat()
    manual=c.execute("SELECT enabled FROM organization_products WHERE organization_id=? AND product='INTENT_RADAR'",(org,)).fetchone()
    ai=c.execute('SELECT calls,reserved_tokens FROM intent_analysis_usage WHERE organization_id=? AND day=?',(org,today)).fetchone()
    counts=c.execute("""SELECT (SELECT COUNT(*) FROM intent_discoveries WHERE organization_id=? AND created_at>=?) searches,
      (SELECT COUNT(*) FROM intent_monitors WHERE organization_id=? AND status<>'Archived') monitors,
      (SELECT COUNT(*) FROM organization_memberships WHERE organization_id=? AND status='ACTIVE') seats,
      (SELECT COUNT(*) FROM intent_monitors WHERE organization_id=? AND status='Active') active_monitors""",(org,today,org,org,org)).fetchone()
    preferences=c.execute('SELECT configuration_json FROM intent_preferences WHERE organization_id=?',(org,)).fetchone();prefs=json.loads(preferences[0]) if preferences else {}
    limits=[('searches',counts['searches'],s.intent_radar_daily_searches,'Requested searches today',reset,'daily reservation'),('ai_calls',ai['calls'] if ai else 0,min(s.intent_radar_ai_daily_calls,prefs.get('analysis_daily_call_limit',s.intent_radar_ai_daily_calls)),'AI reservations today',reset,'daily reservation'),('ai_tokens',ai['reserved_tokens'] if ai else 0,min(s.intent_radar_ai_daily_tokens,prefs.get('analysis_daily_token_limit',s.intent_radar_ai_daily_tokens)),'AI token capacity reserved',reset,'reserved upper bound; not billed tokens'),('monitors',counts['monitors'],s.intent_radar_monitor_limit,'Stored non-archived monitors',None,'capacity')]
    items=[{'dimension':key,'used':used,'limit':limit,'remaining':max(0,limit-used),'label':label,'resets_at':at,'basis':basis,'enforced':True,'near_limit':used>=limit*.8} for key,used,limit,label,at,basis in limits]
    from app.platform.provider_usage import summary
    actual=summary(c)
    sources=[dict(r) for r in c.execute('SELECT provider,reserved_requests FROM intent_source_usage WHERE organization_id=? AND day=?',(org,today)).fetchall()]
    from app.billing import commercial,contracts
    paid=contracts.active(c,org)
    is_trial=bool(paid and (paid.get('is_trial') or paid.get('source_kind')=='TRIAL'))
    internal_testing_payload=None
    if paid:
        from app.billing.access_periods import ledgers
        usage_table,_=ledgers(c,org)
        from app.billing.accounts import anchor,enabled as shared,capacity_used
        billing_org=anchor(c,org)
        saved=contracts.snapshot(paid)
        usage_start=paid.get('usage_period_start',paid['paid_start'])
        usage_end=paid.get('usage_period_end',paid['paid_end'])
        grant=paid.get('internal_testing')
        monthly={r['dimension']:dict(r) for r in c.execute(f'SELECT * FROM {usage_table} WHERE organization_id=? AND contract_id=? AND period_start=?',(billing_org,paid['id'],usage_start)).fetchall()}
        period_end=datetime.fromtimestamp(usage_end,timezone.utc).isoformat()
        for definition in commercial.catalog()['limit_definitions']:
            dim=definition['key'];limit=saved['limits'][dim]
            if dim in contracts.CAPACITY:
                used=counts['active_monitors'] if dim=='monitors' else counts['seats'];reserved=0
                if shared(org):used=capacity_used(c,billing_org,dim,all_monitors=is_trial)
                basis='capacity under temporary internal testing allowance' if grant else 'capacity under 3-day trial terms' if paid.get('is_trial') else 'capacity under saved subscription terms'
            else:
                value=monthly.get(dim,{})
                used=value.get('used',0);reserved=value.get('reserved',0)
                basis='temporary internal testing allowance (auto-expires)' if grant else '3-day card trial; includes reserved capacity' if paid.get('is_trial') else 'approved trial; includes reserved capacity' if paid.get('source_kind')=='TRIAL' else 'verified paid period; includes reserved capacity'
            items.append({'dimension':'plan_'+dim,'used':used+reserved,'reserved':reserved,'limit':limit,'remaining':max(0,limit-used-reserved),'label':definition['label'],'resets_at':period_end if dim not in contracts.CAPACITY else None,'basis':basis,'enforced':True,'near_limit':used+reserved>=limit*.8})
        total=lambda dim:monthly.get(dim,{}).get('used',0)+monthly.get(dim,{}).get('reserved',0)
        search_breakdown={'manual_searches':max(0,total('searches')-total('monitor_executions')),'scheduled_checks':total('monitor_executions'),'total_searches':total('searches'),'reset_at':period_end}
        if grant:
            base_rows=c.execute(f'SELECT dimension,used,reserved FROM {usage_table} WHERE organization_id=? AND contract_id=? AND period_start=?',(org,paid['id'],paid['paid_start'])).fetchall()
            internal_testing_payload={'active':True,'expires_at':grant['expires_at'],'base_entitlement':paid.get('entitlement_label'),'base_limits':paid.get('base_limits'),'base_usage':{r['dimension']:r['used']+r['reserved'] for r in base_rows}}
    else:search_breakdown=None
    from app.billing import access_periods,fixed_term
    native=access_periods.managed(c,org)
    native_access={'managed':True,'active':bool(paid),'kind':'TRIAL' if paid and paid.get('is_trial') else (paid['source_kind'] if paid else None),'recurring':bool(paid and paid.get('source_kind')=='SUBSCRIPTION' and not paid.get('cancel_confirmed_at')),'starts_at':paid['paid_start'] if paid else None,'expires_at':paid['paid_end'] if paid else None} if native else None
    fixed=fixed_term.history(c) if role=='OWNER' and c.execute('SELECT 1 FROM payu_access_orders WHERE organization_id=? LIMIT 1',(org,)).fetchone() else None
    payments=[{'provider':'razorpay',**dict(r)} for r in c.execute('SELECT provider_id,mode,amount,currency,status,recorded_at FROM billing_payments WHERE organization_id=? ORDER BY recorded_at DESC,provider_id DESC LIMIT 50',(org,)).fetchall()] if role in ('OWNER','ADMIN') else []
    commercial_data={'catalog':commercial.catalog(),'provider':'creem','checkout_enabled':s.subscription_checkout_enabled,'blockers':[],'historical_payments':payments,**({'fixed_term':fixed} if fixed is not None else {})}
    access_kind=paid['entitlement_label'] if paid and paid.get('entitlement_label') else 'Seven-day trial' if paid and paid.get('source_kind')=='TRIAL' else 'Fixed-term access' if paid and paid.get('source_kind')=='PAYMENT' else 'Commercial subscription' if paid else 'Expired or unpaid access' if native else 'Approved Beta' if manual and manual[0] else 'Restricted'
    subscription_summary={'status':paid['status'],'provider_status':paid.get('provider_status',paid['status']),'mode':paid['mode'],'plan_code':paid.get('plan_code'),'is_trial':is_trial,'entitlement_label':paid.get('entitlement_label'),'period_start':paid['paid_start'],'period_end':paid['paid_end'],'trial_start':paid.get('trial_start'),'trial_end':paid.get('trial_end'),'cancel_confirmed_at':paid.get('cancel_confirmed_at'),'catalog_version':paid['catalog_version']} if paid else None
    payload={'native_access':native_access,'access':{'kind':access_kind,'is_trial':is_trial,'intent_radar':bool(manual and manual[0] or paid),'growth_intelligence':bool(s.intent_radar_growth_enabled and (manual and manual[0] or paid)),'commercial_subscription':bool(paid and not is_trial)},'subscription':subscription_summary,'search_usage':search_breakdown,'usage':items,'provider_usage':actual,'source_requests':sources,'team_seats':counts['seats'],'commercial_pricing_approved':True,'commercial':commercial_data,'live_payments_enabled':False,'sandbox_tools_available':False,'billing_timezone':'UTC','unmetered':['Exports are bounded per request; no separate export-plan allowance is claimed.','Commercial reports consume both report and shared AI allowances; Beta access retains independent operator limits.'],'support_url':'mailto:contact@planebyte.com?subject=Workspace%20access%20and%20allowances'}
    if internal_testing_payload:
        payload['internal_testing']=internal_testing_payload
    from app.billing import subscription_access,subscriptions
    if subscription_access.required(c,org):
        life=subscriptions.lifecycle(c,org,ctx.actor)
        payload['billing_phase']=life['phase'];active=bool(paid)
        payload['access'].update(intent_radar=active,growth_intelligence=bool(active and s.intent_radar_growth_enabled),kind=life['effective_label'] or ('Trial Ended' if life['phase']=='trial_ended' else 'No active subscription'))
    if paid and paid.get('source_kind')=='COMPLIMENTARY':
        payload['billing_phase']='complimentary';payload['access'].update(kind=paid['entitlement_label'],commercial_subscription=False)
    return payload
