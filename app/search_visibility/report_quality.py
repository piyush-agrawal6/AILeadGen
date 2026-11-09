"""Preserved report/content validation for historical assessment snapshots.

No provider calls, send orchestration or Lead Engine qualification.
"""
import json,re
from app.reports.opportunity import plan,report_issues,email_observation,findings,company_signature
from app.mail.config import mail_settings

def issues(c,pid,body,*,settings=None):
 if body.get('message_type','FIRST_CONTACT')!='FIRST_CONTACT':return []
 from app.platform.modules import legacy_enabled
 if body.get('outreach_strategy')=='WORKSPACE' or not legacy_enabled():
  from app.mail.workspace_templates import quality
  return quality(c,pid,body)
 if body.get('outreach_strategy')=='FIXED_5':
  from app.outreach.fixed import quality
  return quality(c,pid,body)
 errors=[];report=None
 if body.get('report_id'):report=c.execute("SELECT snapshot_json,status FROM client_reports WHERE id=? AND prospect_id=?",(body['report_id'],pid)).fetchone()
 if not report or report['status']!='READY':return ['A ready client PDF attachment is required.']
 data=json.loads(report['snapshot_json'])
 if data.get('report_type')=='OPPORTUNITY_BRIEF_V2':
  from app.experiments.runtime import quality_issues
  return quality_issues(c,pid,body,data)
 p=plan(data,body.get('template_id') if body.get('template_id') in ('website','seo','security','combined') else None,allowed_kinds=body.get('pitch_types') or None)
 from app.reports.data import brand_config
 current_revision=brand_config(c).get('configuration_revision')
 if current_revision and current_revision!=data.get('brand',{}).get('configuration_revision'):errors.append('Approved company settings changed. Regenerate the PDF and email preview.')
 errors.extend(report_issues(data,p))
 if (data.get('sales_review') or {}).get('content_version')!=2:errors.append('Regenerate the report using the current opportunity format.')
 text=body.get('body_text','');lower=text.lower()
 if data['business']['name'].lower() not in lower:errors.append('Name the specific company.')
 matched=[r for r in findings(data) if any(phrase.lower().rstrip('.') in lower for phrase in (email_observation(r,data['business']),r['observation'],r['evidence']))]
 if len(matched)<2:errors.append('Include at least two meaningful, distinct stored findings in business language.')
 paragraphs=[v.strip() for v in text.split('\n\n') if v.strip()]
 opening=paragraphs[1].lower() if len(paragraphs)>1 else ''
 if data['business']['name'].lower() not in opening or 'review' not in opening or 'website' not in opening:errors.append('Use a company-specific website review opening.')
 if not re.search(r'\b(?:may|can|could)\s+(?:affect|improve|support|create|add|reduce|make|help)\b.{0,180}(?:trust|usability|experience|journey|enquiry|search|reliability|visibility|contact|friction)',lower,re.S):errors.append('Explain the potential business consequence without a guarantee.')
 if not re.search(r'planebyte\s+(?:can|will|would|helps?)\s+(?:address|rebuild|improve|implement|modernis[ez]e|review|connect)',lower):errors.append('Explain the specific PlaneByte solution.')
 configured_cta=str(p.get('cta') or '').strip().lower()
 if 'reply' not in lower or not (configured_cta and configured_cta in lower or any(phrase in lower for phrase in ('priority order','implementation scope','tackling first'))):errors.append('Invite a reply for the configured next step.')
 if p['included'] and not all(item['title'].lower() in lower for item in p['included']):errors.append('Explain the configured included value for the eligible project.')
 if company_signature(data,settings or mail_settings()) not in text:errors.append('Use the approved configured sender signature.')
 if re.search(r'{{|}}|\[INSERT|\[COMPANY',text+body.get('subject','')):errors.append('Resolve all template placeholders.')
 if any(x in lower for x in ('i reviewed the available public website evidence','would a short discussion be useful','unlock your potential','game-changing','increase revenue 300%','while researching','while reviewing businesses','viewport declaration','reviewed html')):errors.append('Generic or unsupported sales copy requires review.')
 words=len(text.split())
 if not 100<=words<=170:errors.append('Keep the outreach body between 100 and 170 words, including its signature.')
 return list(dict.fromkeys(errors))

def validate_pdf(content,report_type="FULL_AUDIT"):
 if report_type=="OPPORTUNITY_BRIEF_V2":
  from app.experiments.brief import validate
  return validate(content)
 from io import BytesIO
 from pypdf import PdfReader
 reader=PdfReader(BytesIO(content));text='\n'.join(p.extract_text() or '' for p in reader.pages)
 errors=[]
 if not 6<=len(reader.pages)<=8:errors.append('Client report must contain 6–8 focused pages.')
 if text.lower().count('not assessed')>2:errors.append('Missing measurements dominate the report.')
 if '{{' in text or '}}' in text:errors.append('Report contains unresolved placeholders.')
 if 'REPLY TO THE EMAIL' not in text or 'PlaneByte' not in text:errors.append('Report requires a company value proposition and reply CTA.')
 if errors:raise ValueError('Needs Review: '+' '.join(errors))
 return len(reader.pages)
