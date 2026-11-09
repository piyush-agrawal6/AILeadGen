"""DNS evidence is not recipient verification; no SMTP probing."""
import dns.resolver
from app.acquisition.policy import valid_email

def check(email,timeout=2):
    email=valid_email(email)
    result={'state':'UNKNOWN','syntax_valid':bool(email),'domain_valid':None,'mx_available':None,'role_based':False,'disposable_risk':'UNKNOWN','recipient_delivery_verified':False}
    if not email:result['state']='INVALID';return result
    local,domain=email.rsplit('@',1);result['state']='SYNTAX_VALID';result['role_based']=local in ('info','hello','contact','support','sales','admin','office','reservations','booking')
    resolver=dns.resolver.Resolver();resolver.lifetime=timeout;resolver.timeout=timeout
    try:
        answers=resolver.resolve(domain,'MX')
        hosts=[str(answer.exchange).rstrip('.') for answer in answers]
        if not hosts or hosts==['']:result.update(state='INVALID',domain_valid=True,mx_available=False)
        else:result.update(state='MX_AVAILABLE',domain_valid=True,mx_available=True)
    except dns.resolver.NXDOMAIN:result.update(state='INVALID',domain_valid=False,mx_available=False)
    except dns.resolver.NoAnswer:
        result['mx_available']=False
        try:
            if resolver.resolve(domain,'A'):result.update(state='DOMAIN_VALID',domain_valid=True)
        except dns.resolver.NXDOMAIN:result.update(state='INVALID',domain_valid=False)
        except Exception:result['state']='UNCERTAIN'
    except Exception:result['state']='UNCERTAIN'
    return result
