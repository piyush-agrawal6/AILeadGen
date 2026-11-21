"""Commercial reservations and workspace seat/monitor admission."""
from app.platform.context import organization

def reserve(c,amounts,request_id):
    organization()
    if not isinstance(request_id,str) or not request_id.strip() or len(request_id)>200:raise ValueError('A bounded, stable operation reservation is required.')
    from app.billing.commercial_usage import reserve as commercial_reserve
    return commercial_reserve(c,amounts,request_id)

def capacity(c,dimension,current_count):
    return capacity_for_workspace(c,organization(),dimension,current_count)

def capacity_for_workspace(c,org,dimension,current_count,*,incoming=None):
    if dimension not in ('monitors','team_members'):raise ValueError('Unsupported capacity dimension.')
    from app.billing import access_periods,commercial_usage
    native=access_periods.require_current(c,org)
    if dimension!='monitors' or native and (native.get('source_kind')=='TRIAL' or (native.get('is_trial') and not native.get('internal_testing'))):
        commercial_usage.capacity(c,org,dimension,current_count,incoming=incoming)
