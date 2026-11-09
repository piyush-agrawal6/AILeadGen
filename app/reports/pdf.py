"""Print-designed PlaneByte PDF. No browser fetches or executable client content."""
from datetime import datetime,timezone
from html import escape
from io import BytesIO
from pathlib import Path
import re
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import BaseDocTemplate,Frame,PageTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,KeepTogether,Flowable,Image
from app.reports.copy import KIND_NAMES,explanation
from app.reports.metrics import client_metrics

ASSETS=Path(__file__).resolve().parents[1]/'exports/assets'
NAVY=colors.HexColor('#EDE9E1');BLUE=colors.HexColor('#FF5A1F');TEAL=colors.HexColor('#B5BFA4')
MUTED=colors.HexColor('#9D9F98');LINE=colors.HexColor('#383C35');PALE=colors.HexColor('#171A17')
PAGE_BG=colors.HexColor('#0F1110')
PAGE_W,PAGE_H=A4;WIDTH=PAGE_W-96
KIND_COLORS={'WEBSITE':'#FF5A1F','SEO':'#EDE9E1','SECURITY':'#A8B596'}
LABELS={'WEBSITE':'Website performance','SEO':'SEO audit score','SECURITY':'Security configuration'}


def fonts():
    for style in ('Regular','Medium','Bold'):
        name='PB'+style
        if name not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont(name,str(ASSETS/('PlaneByteSans-'+style+'.ttf'))))
    pdfmetrics.registerFontFamily('PBRegular',normal='PBRegular',bold='PBBold',italic='PBRegular',boldItalic='PBBold')


def paragraph(text,size=9,color=MUTED,bold=False,leading=None,space=0):
    style=ParagraphStyle('content',fontName='PBBold' if bold else 'PBRegular',fontSize=size,leading=leading or size*1.5,textColor=color,spaceAfter=space,alignment=TA_LEFT,splitLongWords=True,wordWrap='LTR',allowWidows=0,allowOrphans=0)
    return Paragraph(escape(str(text or '')).replace('\n','<br/>'),style)


def mark(c,x,y,size):
    c.drawImage(ImageReader(str(ASSETS/'brand-logo.png')),x,y,width=size,height=size,mask='auto')


def fit(c,text,width,font='PBRegular',size=7):
    text=str(text)
    while text and pdfmetrics.stringWidth(text,font,size)>width:text=text[:-1]
    return text


def report_date(value):
    try:
        from zoneinfo import ZoneInfo
        parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
        if parsed.tzinfo is None:parsed=parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(ZoneInfo('Asia/Kolkata')).strftime('%d %B %Y')
    except (ValueError,KeyError):return str(value)[:10]


class ScoreCard(Flowable):
    def __init__(self,title,metric,kind,width):super().__init__();self.title=title;self.metric=metric;self.kind=kind;self.width=width;self.height=142
    def draw(self):
        c=self.canv;accent=colors.HexColor(KIND_COLORS[self.kind]);c.setFillColor(PALE);c.roundRect(0,0,self.width,self.height,8,fill=1,stroke=0)
        c.setStrokeColor(LINE);c.roundRect(0,0,self.width,self.height,8,fill=0,stroke=1)
        c.setFillColor(accent);c.setFont('PBMedium',8.5);c.drawString(14,119,self.title)
        c.setFillColor(MUTED);c.setFont('PBRegular',7);c.drawString(14,99,'CURRENT SCORE')
        value=self.metric['current'];target=self.metric['target'];increase=self.metric['increase']
        c.setFillColor(NAVY);c.setFont('PBBold',27 if value is not None else 12)
        display=f'{value:g}' if value is not None else 'Not assessed';c.drawString(14,69,display)
        if value is not None:
            c.setFillColor(MUTED);c.setFont('PBRegular',8);c.drawString(14+pdfmetrics.stringWidth(display,'PBBold',27)+5,71,'/100')
            c.setFillColor(NAVY);c.drawString(14,46,f'Proposed target: {target:g}/100' if target is not None else 'Target: to be agreed')
            c.setFillColor(BLUE);c.setFont('PBMedium',8);c.drawString(14,29,f'Target gain: +{increase:g} points' if increase else 'Maintain current score' if target is not None else 'Baseline review required')
            c.setFillColor(LINE);c.roundRect(14,14,self.width-28,4,2,fill=1,stroke=0);c.setFillColor(BLUE)
            if value:c.roundRect(14,14,(self.width-28)*value/100,4,2,fill=1,stroke=0)
            if target is not None:c.setStrokeColor(NAVY);c.line(14+(self.width-28)*target/100,12,14+(self.width-28)*target/100,20)
        else:
            c.setFillColor(MUTED);c.setFont('PBRegular',7);c.drawString(14,45,'Measured baseline required');c.drawString(14,30,'No numerical uplift claimed')


def section_title(title,description=None):
    result=[paragraph(title,22,NAVY,True,leading=28,space=7)]
    if description:result.append(paragraph(description,9,space=12))
    return result


def callout(title,text,accent=BLUE):
    box=Table([[paragraph(title,10,NAVY,True)],[paragraph(text,9)]],colWidths=[WIDTH])
    box.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),PALE),('BOX',(0,0),(-1,-1),.5,LINE),('LINEBEFORE',(0,0),(0,-1),3,accent),('LEFTPADDING',(0,0),(-1,-1),14),('RIGHTPADDING',(0,0),(-1,-1),14),('TOPPADDING',(0,0),(-1,0),12),('BOTTOMPADDING',(0,-1),(-1,-1),12)]))
    return box


def details(rows):
    table=Table([[paragraph(key,8,MUTED),paragraph(value if value is not None and value!='' else 'Not assessed',8.5,NAVY)] for key,value in rows],colWidths=[145,WIDTH-145])
    table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-1),.4,LINE),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),10),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
    return table


def observed(value):return 'Observed' if value is True else 'Not observed in sampled evidence' if value is False else 'Not assessed'


def client_findings(data,kind):
    items=sorted(data['evidence'].get(kind,[]),key=lambda item:-item['points'])
    # Findings recorded independently of the opportunity score can corroborate
    # these entries; unknown/debug findings never become client-facing copy.
    codes={item['code'] for item in items}
    from app.reports.copy import FINDING_COPY
    for item in data.get('findings',[]):
        if item['code'] in FINDING_COPY and item['code'] not in codes and item['category'].upper()==kind:
            items.append({'code':item['code'],'detail':FINDING_COPY[item['code']][0],'points':0});codes.add(item['code'])
    return [{**explanation(kind,item),'points':item.get('points',0)} for item in items[:4]]


def finding_blocks(data,kind):
    result=[]
    for item in client_findings(data,kind):
        result.append(KeepTogether([Spacer(1,10),paragraph(item['title'],10,NAVY,True,space=4),paragraph('Evidence: '+item['evidence'],8,leading=11,space=3),paragraph('Why it matters: '+item['impact'],8,leading=11,space=3),paragraph('Recommended improvement: '+item['recommendation'],8,leading=11,space=6)]))
    if not result:result.append(paragraph('No specific improvement was established from the available evidence for this area. This does not establish that the entire website has been assessed.',9,space=10))
    return result


def scope_items(data):
    mode=data['mode'];scores=data['scores'];items=[]
    if mode=='NO_WEBSITE':return [('Website design','Create a clear, mobile-friendly home for your services and public contact details.'),('Search-ready foundations','Plan useful service pages, accurate business information and a crawlable structure.'),('Enquiry planning','Define the appropriate enquiry or booking journey and agree how its effectiveness will be measured.')]
    if mode=='UNREACHABLE':return [('Website recovery / redesign','Confirm the intended domain and hosting, restore access, and review whether repair or redesign is the better route.'),('Reassessment after recovery','Once the site is reachable, reassess performance, search foundations and external security configuration before committing to further work.')]
    if mode=='UNASSESSED':return [('Assessment baseline','Review the current public website and agree the evidence needed before recommending an implementation scope.')]
    if (scores.get('WEBSITE') or 0)>=40:items.append(('Website experience and performance','Address the observed usability, navigation, conversion or performance findings on the pages that matter.'))
    if (scores.get('SEO') or 0)>=40:items.append(('Technical and local SEO foundations','Improve the observed page structure, metadata and relevant public business information without making ranking guarantees.'))
    if (scores.get('SECURITY') or 0)>=40:items.append(('External security configuration','Review and test the specific transport, header or cookie observations with the website provider.'))
    return items or [('Focused review','Validate the specific observations with the website owner and prioritise any changes that support the intended customer journey.')]


def render_pdf(data,output):
    from app.reports.opportunity import plan,why_planebyte
    fonts();buffer=BytesIO();p=plan(data);business=data['business'];brand=data['brand'];name=business['name'];date=report_date(data['created_at'])
    def on_page(c,doc):
        c.saveState();c.setFillColor(PAGE_BG);c.rect(0,0,PAGE_W,PAGE_H,fill=1,stroke=0)
        mark(c,48,PAGE_H-65,32);c.setFillColor(NAVY);c.setFont('PBBold',12);c.drawString(91,PAGE_H-53,'PlaneByte')
        c.setFillColor(MUTED);c.setFont('PBRegular',7);c.drawRightString(PAGE_W-48,PAGE_H-48,fit(c,name,260));c.setStrokeColor(LINE);c.line(48,PAGE_H-76,PAGE_W-48,PAGE_H-76);c.restoreState()
    class NumberedCanvas(canvas.Canvas):
        def __init__(self,*args,**kwargs):kwargs['invariant']=1;super().__init__(*args,**kwargs);self.saved=[]
        def showPage(self):self.saved.append(dict(self.__dict__));self._startPage()
        def save(self):
            total=len(self.saved)
            for state in self.saved:
                self.__dict__.update(state);self.setStrokeColor(LINE);self.line(48,43,PAGE_W-48,43);self.setFillColor(MUTED);self.setFont('PBRegular',7);self.drawString(48,30,re.sub(r'^https?://','',brand.get('website','')).rstrip('/'));self.drawRightString(PAGE_W-48,30,f'{date}  |  {self._pageNumber} / {total}');super().showPage()
            super().save()
    doc=BaseDocTemplate(buffer,pagesize=A4,title=p['title']+' for '+name,author='PlaneByte',leftMargin=48,rightMargin=48,topMargin=98,bottomMargin=58)
    doc.addPageTemplates(PageTemplate(id='report',frames=[Frame(48,57,WIDTH,PAGE_H-155,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=on_page))
    story=[]
    def heading(number,title,description):
        if story:story.append(PageBreak())
        story.extend([paragraph(number+' / OPPORTUNITY REVIEW',8,BLUE,True,space=15),*section_title(title,description),Spacer(1,9)])
    def box(title,text):story.extend([KeepTogether([callout(title,text),Spacer(1,13)])])
    heading('01','Executive Opportunity Brief',p['title']+' | Prepared by PlaneByte')
    story.extend([paragraph(name,25 if len(name)<65 else 18,BLUE,True,leading=30,space=8),paragraph(' · '.join(filter(None,[business.get('city'),business.get('country'),business.get('vertical')])),9,space=19)])
    story.append(paragraph(str(len(p['top']))+' opportunities identified',13,NAVY,True,space=13))
    for i,item in enumerate(p['top'],1):box(f'{i:02d}  '+item['title'],item['category']+' · '+item['priority'])
    story.extend([paragraph('RECOMMENDED FOCUS',8,BLUE,True,space=5),paragraph(p['service_title'],14,NAVY,True,space=10),paragraph(p['solution'],10,space=13)])
    if p['included']:box('More than a website redesign',p['value'])
    heading('02','What We Found','The strongest observations from the public pages reviewed, in business terms.')
    for i,item in enumerate(p['top'],1):
        story.append(KeepTogether([paragraph(f'{i:02d}  '+item['category'].upper()+' · '+item['priority'],8,BLUE,True,space=5),paragraph(item['title'],14,NAVY,True,space=8),paragraph('WHAT WE SAW',7,TEAL,True,space=3),paragraph(item['observation'][0].upper()+item['observation'][1:]+'.',9,NAVY,space=6),paragraph('WHY IT MATTERS',7,TEAL,True,space=3),paragraph(item['impact'],9,space=15)]))
    measured=[]
    for kind,label in [('WEBSITE','Lighthouse mobile performance'),('SEO','Lighthouse SEO')]:
        metric=client_metrics(data)[kind]
        if metric['current'] is not None:measured.append(label+': '+str(metric['current'])+'/100')
    if measured:story.extend([paragraph('RECORDED MEASUREMENTS',7,BLUE,True,space=4),paragraph(' · '.join(measured),9,NAVY,space=8)])
    story.append(paragraph('Review boundary: sampled public pages and passive configuration checks. No penetration test, revenue estimate or ranking assessment was performed. Further validation should confirm device behaviour and the agreed enquiry journey.',7,space=6))
    heading('03','Why It Matters to the Business','An improvement case built around the experience of prospective customers.')
    categories={item['category']:item for item in p['top']}
    outcomes={'Visitor trust':'Make the first interaction feel consistent and dependable, before a guest shares information or makes an enquiry. Confirm the secure journey end to end.','Mobile usability':'Make key information, navigation and contact actions comfortable to use on a phone. Validate representative screen sizes instead of relying on a desktop-only review.','Customer journey':'Give interested visitors one clear next step and a predictable route to the right team. Test the path from the landing page to the enquiry destination.','Search presentation':'Help potential customers understand what the page offers before visiting. Validate accurate page descriptions and relevant business information.'}
    for category,item in categories.items():box(category,outcomes.get(category,'Align this part of the website with its business purpose, then validate the agreed improvement against the original observation.'))
    box('A practical decision, not a growth forecast','These observations can help prioritise work. They do not establish lost bookings, revenue, search positions or an active security incident. The business case and implementation scope should be confirmed together.')
    heading('04','What We Would Improve','A prioritised transformation plan, connected to the evidence on page 2.')
    for i,item in enumerate(p['top'],1):
        story.extend([paragraph(f'{i:02d}  '+item['category'],14,NAVY,True,space=8)])
        columns=[callout('CURRENT · OBSERVATION '+str(i),item['title']),callout('PLANEBYTE APPROACH',item['improvement'])]
        table=Table([[paragraph('CURRENT',7,TEAL,True),paragraph('PROPOSED EXPERIENCE',7,BLUE,True)],[paragraph('See observation '+str(i)+' on page 2.',10,NAVY),paragraph(item['improvement'],10,NAVY)]],colWidths=[WIDTH*.36,WIDTH*.64])
        table.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('BACKGROUND',(0,0),(-1,-1),PALE),('BOX',(0,0),(-1,-1),.5,LINE),('LEFTPADDING',(0,0),(-1,-1),13),('RIGHTPADDING',(0,0),(-1,-1),13),('TOPPADDING',(0,0),(-1,-1),10),('BOTTOMPADDING',(0,0),(-1,-1),12)]));story.extend([table,Spacer(1,20)])
    heading('05','Recommended PlaneByte Approach',p['service_title'])
    story.extend([paragraph(p['solution'],12,NAVY,leading=18,space=22)])
    for service in p['services']:
        box(service['title'],service['description']+'\n'+'\n'.join('• '+d for d in service.get('deliverables',[])[:3]))
    if brand.get('report_copy',{}).get('company_description'):story.append(paragraph(brand['report_copy']['company_description'],9,space=10))
    story.extend([Spacer(1,9),paragraph('WHY PLANEBYTE',8,BLUE,True,space=6),paragraph(why_planebyte(p)[0],12,NAVY,True,space=8),paragraph(why_planebyte(p)[1],9,space=8),paragraph(why_planebyte(p)[2],9)])
    heading('06','More Than a Website Redesign' if p['included'] else 'What Is Included','Included value for an eligible website project.' if p['included'] else 'The proposed scope is confirmed in writing before implementation.')
    for item in p['included']:box(item['title']+' · INCLUDED',item['description'])
    if not p['included']:
        for service in p['services']:box(service['title'],service['description'])
    box('Clear scope. Clear responsibilities.','Eligibility and deliverables are agreed in a written proposal. Third-party subscriptions, hosting and separately scoped work are confirmed before commitment. No artificial monetary values or guaranteed outcomes are attached to this review.')
    heading('07','Implementation Roadmap','Six clear stages from evidence to a validated launch.')
    phases=[('Discovery','Confirm the findings, audience, priority pages and business requirements.'),('Design','Agree the relevant page hierarchy, mobile experience and primary enquiry actions.'),('Development','Implement the approved website or focused technical improvements.'),('SEO + technical setup','Configure the agreed search foundations and relevant public technical settings.'),('QA + launch','Test the approved journeys and deployment before releasing changes.'),('Post-launch validation','Recheck the agreed scope and document the results and handover.')]
    for i,(title,text) in enumerate(phases,1):box(f'{i:02d}  '+title,text)
    heading('08','A Stronger Digital Experience','Let’s turn these opportunities into a practical implementation plan.')
    story.extend([Spacer(1,18),paragraph('Your priorities.\nA clear way forward.',29,NAVY,True,leading=36,space=25),paragraph('If these priorities align with your plans, we would be happy to review the findings together and outline a practical implementation approach.',12,NAVY,leading=19,space=24)])
    box('REPLY TO THE EMAIL',p['cta'])
    story.extend([Spacer(1,28),paragraph('PlaneByte',21,BLUE,True,space=10),paragraph(brand.get('signature_tagline','Software Engineering · SEO · Security'),11,NAVY,space=18)])
    for value in [brand.get('website'),brand.get('contact_email')]:
        if value:story.append(paragraph(value,11,BLUE,space=7))
    story.append(Spacer(1,20));story.append(paragraph('Prepared from the stored public review dated '+date+'. This is an opportunity assessment; implementation scope and validation are agreed with the business.',8))
    doc.build(story,canvasmaker=NumberedCanvas)
    from pypdf import PdfReader,PdfWriter
    writer=PdfWriter();writer.clone_document_from_reader(PdfReader(BytesIO(buffer.getvalue())))
    try:stamp=datetime.fromisoformat(data['created_at'].replace('Z','+00:00')).astimezone(timezone.utc).strftime("D:%Y%m%d%H%M%S+00'00'")
    except ValueError:stamp="D:20000101000000+00'00'"
    writer.add_metadata({'/Title':p['title']+' for '+name,'/Author':'PlaneByte','/Subject':'Business opportunities, recommended implementation and included value','/CreationDate':stamp,'/ModDate':stamp})
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('wb') as f:writer.write(f)
    return output
