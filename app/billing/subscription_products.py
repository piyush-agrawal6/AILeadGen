"""Owner-authorized catalog configuration through the official Creem API."""
import hashlib,json
from app.billing import commercial,creem
from app.database.prospects import now

def configure(mode):
 result=[]
 for plan in commercial.catalog()['plans']:
  if plan['code']=='enterprise':continue
  for variant in ('paid','trial'):
   external='planebyte-v2-'+plan['code']+'-monthly-'+variant
   found=creem.request('GET','/products/search',mode=mode,params={'external_id':external,'page_size':10})
   items=found.get('items',[])
   if len(items)>1:raise creem.Rejected('Ambiguous Creem product mapping.')
   if items:product=items[0]
   else:
    body={'name':'PlaneByte '+plan['name']+(' — 3-day card trial' if variant=='trial' else ''),
     'description':'Intent Radar + Growth Intelligence. '+('72-hour card-required trial, then ' if variant=='trial' else '')+'USD '+str(plan['monthly_minor']//100)+' each month until canceled.',
     'price':plan['monthly_minor'],'currency':'USD','billing_type':'recurring','billing_period':'every-month',
     'tax_mode':'inclusive','tax_category':'saas','business_net_pricing':False,
     'external_id':external,'metadata':{'planebyte_plan':plan['code'],'planebyte_variant':variant,'catalog_version':commercial.catalog()['version']},
     'abandoned_cart_recovery_enabled':False,'default_success_url':'https://app.planebyte.com/onboarding?payment=returned'}
    if variant=='trial':body.update(trial_period_days=3,trial_price=0)
    product=creem.request('POST','/products',mode=mode,body=body,idempotency_key=hashlib.sha256(external.encode()).hexdigest())
   product=creem.validate_product(creem.get_product(product['id'],mode=mode),plan,variant,mode)
   result.append({'provider':'creem','environment':mode,'plan_code':plan['code'],'variant':variant,'product_id':product['id'],
    'price_minor':plan['monthly_minor'],'currency':'USD','interval':'every-month','trial_days':3 if variant=='trial' else 0,
    'catalog_hash':commercial.catalog()['catalog_sha256'],'verified_json':json.dumps(product,sort_keys=True),'verified_at':now()})
 return result

def persist(c,rows):
 for row in rows:
  existing=c.execute('SELECT * FROM subscription_products WHERE provider=? AND environment=? AND plan_code=? AND variant=?',tuple(row[k] for k in ('provider','environment','plan_code','variant'))).fetchone()
  if existing and existing['product_id']!=row['product_id']:raise creem.Rejected('Existing product attribution requires review.')
  keys=tuple(row)
  c.execute('INSERT INTO subscription_products('+','.join(keys)+') VALUES('+','.join('?' for _ in keys)+') ON CONFLICT(provider,environment,plan_code,variant) DO UPDATE SET price_minor=excluded.price_minor,currency=excluded.currency,interval=excluded.interval,trial_days=excluded.trial_days,catalog_hash=excluded.catalog_hash,verified_json=excluded.verified_json,verified_at=excluded.verified_at',tuple(row[k] for k in keys))
