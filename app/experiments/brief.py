"""Opportunity Brief V2: three fixed, evidence-led pages; full PDF is untouched."""
from pathlib import Path
from html import escape
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from app.reports.pdf import fonts,mark,PAGE_W,PAGE_H,PAGE_BG,PALE,LINE,NAVY,MUTED,BLUE
from app.experiments.content import select_findings,evidence,AEO_CODES,CYBER_CODES,CTA
WIDTH=PAGE_W-88

def issues(data):
 from app.experiments.content import eligible_templates
 errors=[]
 if not data.get('business',{}).get('name'):errors.append('Company required.')
 if data.get('mode')!='REACHABLE':errors.append('A reachable, analyzed public website is required.')
 template=data.get('experiment',{}).get('template_id')
 if template not in eligible_templates(data):errors.append('Insufficient relevant evidence for assigned strategy.')
 if not data.get('brand',{}).get('website'):errors.append('Configured PlaneByte website required.')
 return errors

def render_pdf(data,output):
 errors=issues(data)
 if errors:raise ValueError('Needs Review: '+' '.join(errors))
 fonts();output=Path(output);output.parent.mkdir(parents=True,exist_ok=True);c=canvas.Canvas(str(output),pagesize=(PAGE_W,PAGE_H))
 c.setTitle(data['business']['name']+' - Digital Opportunity Brief');c.setAuthor('PlaneByte')
 rows=select_findings(data,data['experiment']['template_id'])[:3]
 for item in evidence(data):
  if len(rows)>=3:break
  if item['code'] not in {r['code'] for r in rows}:rows.append(item)
 business=data['business'];brand=data['brand'];web=brand.get('website') or 'https://planebyte.com';email=brand.get('contact_email') or 'contact@planebyte.com'
 def text(value,x,y,width=WIDTH,size=10,color=NAVY,bold=False,max_height=120):
  p=Paragraph(escape(str(value or '')).replace('\n','<br/>'),ParagraphStyle('brief',fontName='PBBold' if bold else 'PBRegular',fontSize=size,leading=size*1.42,textColor=color,splitLongWords=True))
  _,height=p.wrap(width,max_height)
  if height>max_height:raise ValueError('Brief content exceeds reviewed layout bounds.')
  p.drawOn(c,x,y-height);return y-height
 def base(page,label):
  c.setFillColor(PAGE_BG);c.rect(0,0,PAGE_W,PAGE_H,fill=1,stroke=0);mark(c,44,PAGE_H-77,32)
  text('PLANEBYTE',87,PAGE_H-44,size=10,bold=True);text('OPPORTUNITY BRIEF V2',87,PAGE_H-60,size=7,color=MUTED)
  c.setStrokeColor(LINE);c.line(44,54,PAGE_W-44,54)
  text('PUBLIC WEBSITE REVIEW · '+str(data.get('created_at',''))[:10],44,41,size=6.7,color=MUTED)
  text(f'{page:02} / 03   {label}',PAGE_W-196,41,width=152,size=6.7,color=MUTED)
 def card(y,heading,body,detail=None,height=126):
  c.setFillColor(PALE);c.setStrokeColor(LINE);c.roundRect(44,y-height,WIDTH,height,9,fill=1,stroke=1)
  c.setFillColor(BLUE);c.roundRect(44,y-height,3,height,1,fill=1,stroke=0)
  yy=text(heading,61,y-17,width=WIDTH-34,size=11,bold=True,max_height=42)-10
  yy=text(body,61,yy,width=WIDTH-34,size=9.5,max_height=64)
  if detail:text(detail,61,yy-8,width=WIDTH-34,size=7,color=MUTED,max_height=28)
  return y-height-15
 base(1,'OPPORTUNITIES')
 y=text('Digital Opportunity\nBrief',44,PAGE_H-109,size=33,bold=True,max_height=110)-18
 y=text(business['name'],44,y,size=19 if len(business['name'])<65 else 14,bold=True,max_height=66)-8
 y=text(' · '.join(v for v in (business.get('vertical'),business.get('city'),business.get('country')) if v),44,y,size=9,color=MUTED,max_height=38)-24
 y=text('TOP OPPORTUNITIES',44,y,size=8,color=BLUE,bold=True)-13
 for index,row in enumerate(rows):
  family='AI search / AEO readiness' if row['code'] in AEO_CODES else 'External security / technical trust' if row['code'] in CYBER_CODES else 'Supporting website experience'
  y=card(y,f'{index+1:02}  {family}',row['title']+'. '+row['impact'],row['priority'],height=110 if len(rows)==3 else 136)
 if y<76:raise ValueError('Brief cover overflow.')
 c.showPage();base(2,'EVIDENCE')
 y=text('What We Found',44,PAGE_H-113,size=28,bold=True)-14
 y=text('Observed public evidence, with a practical interpretation. These findings do not establish AI visibility, search rankings, a vulnerability or a security breach.',44,y,size=10,color=MUTED,max_height=55)-24
 for index,row in enumerate(rows):
  detail=row['observation'] if row['observation'].casefold().strip(' .')!=row['evidence'].casefold().strip(' .') else None
  y=card(y,f'{index+1:02}  Evidence reference',row['evidence'],detail,height=145 if len(rows)==3 else 175)
 source=business['website'];y=text('SOURCE',44,y-4,size=7,color=BLUE,bold=True)-8
 y2=text(source,44,y,size=8,width=WIDTH,max_height=40);c.linkURL(source,(44,y2,PAGE_W-44,y),relative=0,thickness=0)
 text('Scope: sampled public pages and passive external configuration. Findings may change; validate implementation scope before making changes.',44,y2-13,size=8,color=MUTED,max_height=45)
 c.showPage();base(3,'NEXT STEP')
 y=text('What PlaneByte\nWould Prioritize',44,PAGE_H-113,size=28,bold=True,max_height=90)-24
 for index,row in enumerate(rows):
  action=row['improvement']
  y=card(y,f'{index+1:02}  '+('Search-ready information' if row['code'] in AEO_CODES else 'Technical trust' if row['code'] in CYBER_CODES else 'Customer journey'),action,height=92)
 y=text('SOFTWARE ENGINEERING · AI SEARCH / AEO · SEO · CYBERSECURITY',44,y-7,size=7,color=BLUE,bold=True,max_height=25)-17
 y=text("Reply to the email and we can send the recommended priority order and implementation scope.",44,y,size=15,bold=True,max_height=65)-17
 y=text('PlaneByte can review the observed foundations and implement agreed improvements. A full website rebuild is not assumed; priorities and responsibilities are agreed together.',44,y,size=9,color=MUTED,max_height=50)-16
 low=text(web,44,y,size=11,color=BLUE,bold=True,max_height=24);c.linkURL(web,(44,low,330,y),relative=0,thickness=0)
 low2=text(email,44,low-11,size=9,color=NAVY,max_height=22);c.linkURL('mailto:'+email,(44,low2,330,low-11),relative=0,thickness=0)
 if low2<70:raise ValueError('Brief final-page overflow.')
 c.save();return output

def validate(content):
 from io import BytesIO
 from pypdf import PdfReader
 r=PdfReader(BytesIO(content));text='\n'.join(p.extract_text() or '' for p in r.pages)
 if len(r.pages) not in (2,3) or 'Digital Opportunity' not in text or 'What We Found' not in text or 'Reply to the email' not in text:raise ValueError('Opportunity Brief format/CTA is invalid.')
 if any(x in text for x in ('{{','}}','[INSERT','Not assessed')):raise ValueError('Brief contains missing data or placeholders.')
 if sum(len(p.get('/Annots',[])) for p in r.pages)<3:raise ValueError('Clickable source and PlaneByte links required.')
 return len(r.pages)
