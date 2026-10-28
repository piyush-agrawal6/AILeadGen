"""Client measurements and explicit planning goals, separate from sales scores."""
import math

# A pass is never inferred from the absence of a finding. Old snapshots can
# establish a failed header check, but usually cannot establish passing headers.
HEADER_CHECKS = (
    ('HSTS', 'NO_HSTS'),
    ('Content Security Policy', 'NO_CSP'),
    ('Content-type protection', 'NO_NOSNIFF'),
    ('Frame-embedding protection', 'NO_FRAME_PROTECTION'),
    ('Referrer Policy', 'NO_REFERRER_POLICY'),
    ('Permissions Policy', 'NO_PERMISSIONS_POLICY'),
)


def valid_score(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):return None
    return round(float(value),1) if 0<=value<=100 else None


def client_metrics(data):
    reachable=data.get('mode')=='REACHABLE'
    lh=data.get('lighthouse',{})
    targets=data.get('brand',{}).get('score_targets',{})
    def metric(current,goal,source):
        current=valid_score(current) if reachable else None
        goal=valid_score(goal)
        target=max(current,goal) if current is not None and goal is not None else None
        return {'current':current,'target':target,'increase':round(target-current,1) if target is not None else None,'source':source}
    result={
        'WEBSITE':metric(lh.get('performance_score'),targets.get('WEBSITE',90),'Lighthouse mobile performance'),
        'SEO':metric(lh.get('seo_score'),targets.get('SEO',100),'Lighthouse SEO audit'),
    }
    codes={item.get('code') for item in data.get('evidence',{}).get('SECURITY',[])}
    checks=[]
    https=data.get('website',{}).get('https_enabled') if reachable else None
    checks.append({'name':'HTTPS transport','result':'PASS' if https is True else 'FAIL' if https is False else 'UNKNOWN'})
    persisted=data.get('website',{}).get('security_checks',{})
    for name,code in HEADER_CHECKS:
        value=persisted.get(code)
        state='FAIL' if reachable and (code in codes or value is False) else 'PASS' if reachable and value is True else 'UNKNOWN'
        checks.append({'name':name,'result':state})
    assessed=sum(item['result']!='UNKNOWN' for item in checks)
    passed=sum(item['result']=='PASS' for item in checks)
    score=round(100*passed/len(checks)) if assessed==len(checks) else None
    result['SECURITY']={**metric(score,targets.get('SECURITY',100),'Seven-check external configuration checklist'),'checks':checks,'assessed':assessed,'passed':passed,'total':len(checks)}
    return result
