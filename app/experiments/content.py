"""Five deliberate strategies; substitutions come only from stored public evidence."""
import hashlib,re
from app.reports.opportunity import findings,email_observation,sentences,company_signature
from app.experiments.plan import TEMPLATES
VERSION=1;BRIEF_VERSION=2
CTA="Reply and I'll send the first three changes we'd prioritize and a rough implementation scope."
AEO_CODES={'MISSING_SCHEMA','MISSING_META_DESCRIPTION','MISSING_TITLE','MISSING_H1','MULTIPLE_H1','NO_CITY_REFERENCE','NO_CONTACT_PAGE','ROBOTS_NOT_OBSERVED','SITEMAP_NOT_OBSERVED','BROKEN_LINKS'}
CYBER_CODES={'HTTP_ONLY','NO_CSP','NO_HSTS','NO_FRAME_PROTECTION','NO_NOSNIFF','NO_REFERRER_POLICY','NO_PERMISSIONS_POLICY','INSECURE_FORM_ACTION','CERTIFICATE_VERIFICATION_FAILED'}
SUBJECTS={
 'AEO_READINESS':('AI-search readiness for {company}','A quick AI-search review for {company}'),
 'LOCAL_AEO':('A local + AI search opportunity for {company}','{company} - search visibility review'),
 'CYBER_AUDIT':('A quick external security review for {company}','Technical trust findings for {company}'),
 'AEO_CYBER':('2 visibility + trust opportunities for {company}','A quick digital review for {company}'),
 'THREE_FINDINGS':('3 quick findings for {company}','Three public website observations for {company}')}

def evidence(data):
 rows=[dict(r) for r in findings(data) if r['points']>0]
 for row in rows:
  if row['code']=='HTTP_ONLY':row.update(title='Make the encrypted visitor journey consistent',observation='an HTTP version remained accessible in the reviewed public journey',impact='Visitors using that HTTP address may remain on an unencrypted connection; consistent redirects can strengthen technical trust.')
 return rows
def groups(data):
 rows=evidence(data);return rows,[r for r in rows if r['code'] in AEO_CODES],[r for r in rows if r['code'] in CYBER_CODES]
def eligible_templates(data):
 rows,aeo,cyber=groups(data);out=[]
 if len(aeo)>=2:out.extend(['AEO_READINESS','LOCAL_AEO'])
 if len(cyber)>=2:out.append('CYBER_AUDIT')
 if aeo and cyber:out.append('AEO_CYBER')
 if len(rows)>=3:out.append('THREE_FINDINGS')
 return out

def select_findings(data,template):
 rows,aeo,cyber=groups(data)
 if template not in eligible_templates(data):raise ValueError('Template does not have enough relevant stored evidence.')
 return (aeo[:2] if template in ('AEO_READINESS','LOCAL_AEO') else cyber[:2] if template=='CYBER_AUDIT' else [aeo[0],cyber[0]] if template=='AEO_CYBER' else rows[:3])

def pitch(data,template):
 if template in ('AEO_READINESS','LOCAL_AEO'):return ('AEO' if template=='AEO_READINESS' else 'SEO_AEO'),None
 if template=='CYBER_AUDIT':return 'CYBER',None
 if template=='AEO_CYBER':return 'AEO_CYBER','AEO' if groups(data)[1][0]['points']>=groups(data)[2][0]['points'] else 'CYBER'
 return 'THREE_FINDINGS',('AEO' if groups(data)[1] else 'CYBER' if groups(data)[2] else None)

def assign_template(data,seed,counts=None):
 eligible=eligible_templates(data)
 if not eligible:raise ValueError('Needs Review: no supported experiment strategy has sufficient evidence.')
 counts=counts or {};return min(eligible,key=lambda key:(counts.get(key,0),hashlib.sha256((seed+key).encode()).hexdigest()))

def openings(data,template):
 company=data['business']['name'];city=data['business'].get('city')
 if template=='AEO_READINESS':return [f"I reviewed {company}'s public website for AI-search readiness.",f"Our public website review of {company} focused on search-readiness foundations."]
 if template=='LOCAL_AEO':return [f"We reviewed {company}'s public service and location information"+(f' in {city}.' if city else '.'),f"I reviewed how {company}'s website explains its services and location."]
 if template=='CYBER_AUDIT':return [f"I ran a lightweight external configuration review of {company}'s public website.",f"Our passive public website review of {company} identified two technical-trust observations."]
 if template=='AEO_CYBER':return [f"Our public review of {company} identified a visibility foundation and a technical-trust opportunity.",f"I reviewed {company}'s website for search readiness and external technical trust."]
 return [f"I reviewed {company}'s public web presence and found three things worth looking at:",f"Our public review of {company} surfaced three practical priorities:"]

def subjects(data,template):return [v.format(company=data['business']['name']) for v in SUBJECTS[template]]

async def ai_choice(c,actor,data,template):
 """Gemini may select approved copy, never add evidence, claims or recipients."""
 from typing import Literal
 from pydantic import create_model,ConfigDict
 from app.acquisition.ai import provider,cached
 allowed_subjects=subjects(data,template);allowed_openings=openings(data,template)
 Choice=create_model('ExperimentSubstitutions',__config__=ConfigDict(extra='forbid',strict=True),subject=(Literal[tuple(allowed_subjects)],...),opening=(Literal[tuple(allowed_openings)],...))
 inputs={'template_id':template,'template_version':VERSION,'company':data['business']['name'],'vertical':data['business']['vertical'],'city':data['business']['city'],'verified_findings':[{'code':r['code'],'observation':r['observation']} for r in select_findings(data,template)],'recommended_pitch':pitch(data,template)[0],'allowed_cta':CTA,'allowed_subjects':allowed_subjects,'allowed_openings':allowed_openings}
 async def produce():return await provider(c).structured('Choose one of the provided approved subject and opening strings, exactly. Return only subject/opening; do not invent findings, facts, names, numbers or alternate text.',inputs,Choice)
 result,hit=await cached(c,actor,'EXPERIMENT_COPY_V1',inputs,produce,Choice)
 return {**result.model_dump(),'method':'GEMINI_APPROVED_CHOICES','cached':hit}

def render(data,template,*,subject_variant=0,generation=None,verified_name=None,settings=None):
 from app.mail.config import mail_settings
 rows=select_findings(data,template);company=data['business']['name'];g=generation or {};allowed_subjects=subjects(data,template);allowed_openings=openings(data,template)
 subject=g.get('subject') or allowed_subjects[subject_variant%2];opening=g.get('personalized_opening') or g.get('opening') or allowed_openings[0]
 if subject not in allowed_subjects or opening not in allowed_openings:raise ValueError('Unapproved generated content.')
 name=verified_name if verified_name and re.fullmatch(r"[A-Za-z][A-Za-z .'-]{0,59}",verified_name) else company+' team'
 observed=[email_observation(r,data['business']).rstrip('.') for r in rows]
 for i in range(min(2,len(observed))):
  override=g.get('finding_'+str(i+1)+'_copy')
  if override is not None and override!=observed[i]:raise ValueError('Unsupported finding substitution.')
 if g.get('optional_bridge'):raise ValueError('Unapproved optional bridge.')
 if template=='AEO_READINESS':
  middle='We noticed '+sentences(observed)+'.\n\nThese signals can make services and business information less explicit to search and AI-answer systems. This is a readiness review, not a claim about your visibility in any AI product.\n\nPlaneByte can improve these AEO/SEO foundations without a full website rebuild.'
 elif template=='LOCAL_AEO':
  middle='The sampled pages show '+sentences(observed)+'.\n\nClear service, location and business information can help people and search systems understand the right context for an enquiry.\n\nPlaneByte can strengthen local SEO, accurate structured information and answer-ready service content around these specific gaps.'
 elif template=='CYBER_AUDIT':
  middle='We observed '+sentences(observed)+'.\n\nThese observations do not establish a vulnerability or mean the site is compromised. They can identify configuration worth reviewing for technical trust.\n\nPlaneByte combines software engineering and cybersecurity to review the evidence and implement agreed improvements with your website provider.'
 elif template=='AEO_CYBER':
  middle='We noticed '+observed[0]+', alongside '+observed[1]+'.\n\nTogether, these create a focused opportunity to clarify business information and review public technical trust. Neither establishes a ranking issue or a security breach.\n\nPlaneByte can improve search-readiness foundations and the observed external configuration without assuming you need a rebuild.'
 else:
  middle='\n'.join('• '+x[0].upper()+x[1:]+'.' for x in observed)+'\n\nThe strongest opportunity is '+('clearer search-ready business information' if rows[0]['code'] in AEO_CODES else 'external technical trust' if rows[0]['code'] in CYBER_CODES else 'the evidenced customer journey')+'. These observations may affect clarity, trust or enquiry friction. PlaneByte can translate the findings into a focused implementation scope.'
 signature=company_signature(data,settings or mail_settings())
 text=f"Hi {name},\n\n{opening}\n\n{middle}\n\nI've attached a short evidence brief with the priorities.\n\n{CTA}\n\nBest,\n{signature}"
 result={'subject':subject,'body_text':text,'template_id':template,'template_version':VERSION,'subject_variant':allowed_subjects.index(subject),'primary_pitch':pitch(data,template)[0],'secondary_pitch':pitch(data,template)[1],'finding_codes':[r['code'] for r in rows],'generation_method':g.get('method','APPROVED_DETERMINISTIC')}
 problems=email_issues(data,result)
 if problems:raise ValueError('Needs Review: '+' '.join(problems))
 return result

def email_issues(data,message):
 errors=[];text=message.get('body_text','');low=text.lower();template=message.get('template_id');company=data['business']['name']
 if template not in eligible_templates(data):return ['Relevant verified findings are required for this strategy.']
 if not 70<=len(text.split())<=140:errors.append('Experiment email must contain70–140words.')
 if company.casefold() not in low:errors.append('Specific company required.')
 if text.count(CTA)!=1:errors.append('One approved reply CTA required.')
 if 'planebyte' not in low or 'planebyte.com' not in low:errors.append('PlaneByte solution/signature required.')
 from app.mail.config import mail_settings
 if company_signature(data,mail_settings()) not in text:errors.append('Use the approved PlaneByte signature.')
 if re.search(r'{{|}}|\[INSERT|\[COMPANY',text+message.get('subject','')):errors.append('Unresolved placeholders.')
 if any(x in low for x in ('invisible in ai','do not appear in chatgpt','ai cannot find','guaranteed','300%','security breach detected','compromised website','free audit!!!')):errors.append('Unsupported claim.')
 for item in select_findings(data,template):
  if email_observation(item,data['business']).rstrip('.').casefold() not in low:errors.append('Stored finding substitution changed.')
 return errors
