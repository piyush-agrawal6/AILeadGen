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
    fonts();buffer=BytesIO();business=data['business'];brand=data['brand'];name=business['name'];date=report_date(data['created_at'])
    metrics=client_metrics(data)
    website=brand.get('website','');footer_site=re.sub(r'^https?://','',website).rstrip('/')
    def on_page(c,doc):
        c.saveState()
        c.setFillColor(PAGE_BG);c.rect(0,0,PAGE_W,PAGE_H,fill=1,stroke=0)
        if doc.page==1:
            mark(c,48,PAGE_H-91,44);c.setFillColor(NAVY);c.setFont('PBBold',22);c.drawString(104,PAGE_H-73,'PlaneByte')
            c.setStrokeColor(colors.HexColor('#252A23'));c.setLineWidth(.5)
            for x in range(392,600,28):c.line(x,250,x,600)
            for y in range(250,601,28):c.line(392,y,PAGE_W,y)
            c.setFillColor(colors.HexColor('#1D211D'));path=c.beginPath();path.moveTo(PAGE_W,590);path.lineTo(452,500);path.lineTo(452,400);path.lineTo(PAGE_W,490);path.close();c.drawPath(path,fill=1,stroke=0)
            c.setStrokeColor(colors.HexColor('#56604A'));c.line(452,400,PAGE_W,490)
        else:
            mark(c,48,PAGE_H-65,32);c.setFillColor(NAVY);c.setFont('PBBold',12);c.drawString(91,PAGE_H-53,'PlaneByte')
            c.setFillColor(MUTED);c.setFont('PBRegular',7);c.drawRightString(PAGE_W-48,PAGE_H-48,fit(c,'Digital performance review | '+name,270));c.setStrokeColor(LINE);c.line(48,PAGE_H-76,PAGE_W-48,PAGE_H-76)
        c.restoreState()
    class NumberedCanvas(canvas.Canvas):
        def __init__(self,*args,**kwargs):kwargs['invariant']=1;super().__init__(*args,**kwargs);self.saved=[]
        def showPage(self):self.saved.append(dict(self.__dict__));self._startPage()
        def save(self):
            total=len(self.saved)
            for state in self.saved:
                self.__dict__.update(state);self.setStrokeColor(LINE);self.line(48,43,PAGE_W-48,43);self.setFillColor(MUTED);self.setFont('PBRegular',6.5);self.drawString(48,30,footer_site or 'PlaneByte');self.drawRightString(PAGE_W-48,30,f'{date}  |  Page {self._pageNumber} of {total}');super().showPage()
            super().save()
    doc=BaseDocTemplate(buffer,pagesize=A4,title='Digital performance review for '+name,author='PlaneByte',leftMargin=48,rightMargin=48,topMargin=92,bottomMargin=58)
    doc.addPageTemplates(PageTemplate(id='report',frames=[Frame(48,57,WIDTH,PAGE_H-151,leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=on_page))
    story=[Spacer(1,93),paragraph('WEBSITE / SEO / SECURITY',9,BLUE,True,space=23),paragraph('Digital performance\nreview for',33,NAVY,True,leading=40,space=6),paragraph(name,22 if len(name)>80 else 32,BLUE,True,leading=28 if len(name)>80 else 39,space=18),paragraph('Your current digital performance, a clear improvement plan and measurable goals for the next stage of growth.',11,leading=17,space=25)]
    cover_rows=[('Business',name),('Location',', '.join(filter(None,[business['city'],business['country']]))),('Industry',business['vertical']),('Prepared',date)]
    for title,value in cover_rows:story.extend([paragraph(title.upper(),7,MUTED,space=2),paragraph(value,10,NAVY,space=12)])
    story.extend([Spacer(1,12),callout('Clear evidence. Practical next steps.','Prepared from existing public observations. Recommendations are qualitative and should be validated with the website owner.')])
    story.append(PageBreak())
    story.extend(section_title('Executive summary','Current measured performance and proposed improvement targets.'))
    kinds=['WEBSITE'] if data['mode']!='REACHABLE' else ['WEBSITE','SEO','SECURITY']
    card_width=(WIDTH-10*(len(kinds)-1))/len(kinds)
    cards=[]
    for i,kind in enumerate(kinds):
        if i:cards.append(Spacer(10,1))
        cards.append(ScoreCard(LABELS[kind],metrics[kind],kind,card_width))
    table=Table([cards],colWidths=[10 if isinstance(item,Spacer) else card_width for item in cards]);table.setStyle(TableStyle([('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0)]))
    if data['mode']=='REACHABLE':
        story.extend([table,Spacer(1,12),paragraph('Higher current scores are better. Website = Lighthouse mobile performance; SEO = Lighthouse SEO. Security covers the seven external configuration checks listed in this review.',8,space=8),paragraph('Targets are proposed goals, not forecasts or guarantees. The target gain is the arithmetic difference from the current score; results must be confirmed after implementation and a fresh audit.',8,space=18)])
    mode=data['mode'];primary=data.get('primary')
    summary='Our review identified practical opportunities in '+KIND_NAMES.get(primary,'the available website evidence').lower()+'. The findings below describe what was observed and where a focused improvement could help.'
    if mode=='NO_WEBSITE':summary='No official website was found in the available public sources. The primary opportunity is a new website that makes your services and enquiry path clear. Existing-site SEO and security were not assessed.'
    elif mode=='UNREACHABLE':summary='A website is listed, but the stored assessment did not receive a successful response. The primary opportunity is website recovery or redesign. This is distinct from having no website; SEO and security require reassessment after access is restored.'
    elif mode=='UNASSESSED':summary='A website is listed, but a current website assessment was not available in the stored evidence. No missing scores or findings have been invented.'
    story.extend([callout('Recommended focus: '+('New website' if mode=='NO_WEBSITE' else 'Website recovery / redesign' if mode=='UNREACHABLE' else KIND_NAMES.get(primary,'Further assessment')),summary),Spacer(1,20)])
    if any(client_findings(data,kind) for kind in kinds):story.extend(section_title('Key findings','The following observations are drawn from the assessment already recorded.'))
    for kind in kinds:
        for item in client_findings(data,kind)[:1]:story.append(KeepTogether([paragraph(item['title'],10,NAVY,True,space=3),paragraph(item['evidence'],9,space=11)]))
    if mode=='REACHABLE':
        story.append(PageBreak());story.extend(section_title('Current digital presence','A visual baseline and the strongest opportunities established by the stored assessment.'))
        capture=data.get('capture') or {}
        if data.get('_capture_path'):
            story.extend([Image(data['_capture_path'],width=WIDTH,height=WIDTH*900/1440),Spacer(1,8),paragraph('Public homepage captured '+report_date(capture.get('captured_at',data['created_at']))+'. The image reflects the page at scan time.',7,space=12)])
        else:story.append(callout('Screenshot unavailable',capture.get('reason') or 'No public homepage image was captured for this observation. The report uses the stored technical evidence.'))
        profile=data['website']
        observations=[('Public website','Reachable during the stored assessment.'),('Mobile layout signal','A mobile viewport declaration was observed.' if profile.get('has_viewport') else 'A mobile viewport declaration was not established.'),('Contact journey','A contact page was observed.' if profile.get('has_contact_page') else 'A contact page was not established in the sampled pages.')]
        strongest=sorted([(kind,item) for kind in kinds for item in client_findings(data,kind)],key=lambda pair:-pair[1]['points'])[:3]
        if strongest:observations=[(item['title'],item['evidence']) for _,item in strongest]
        observations.append(('HTTPS','Observed in the stored assessment.' if profile.get('https_enabled') else 'Not established in the sampled evidence.'))
        story.extend([Spacer(1,12),details(observations)])
        story.append(PageBreak());story.extend(section_title('Top 3 improvement priorities','A focused starting point, ordered by the strength of the recorded findings.'))
        priorities=[]
        for kind in kinds:
            for item in client_findings(data,kind):priorities.append((kind,item))
        priorities=sorted(priorities,key=lambda pair:-pair[1]['points'])[:3]
        for index,(kind,item) in enumerate(priorities,1):
            priority='High' if item['points']>=15 else 'Medium' if item['points']>=5 else 'Low'
            effort='Medium' if kind=='WEBSITE' else 'Low to medium'
            story.extend([paragraph(str(index)+'. '+item['title'],13,NAVY,True,space=6),paragraph('Priority: '+priority+' | Potential impact: '+('Customer journey' if kind=='WEBSITE' else 'Search clarity' if kind=='SEO' else 'Configuration consistency')+' | Indicative effort: '+effort,8,BLUE,space=8),paragraph('Finding: '+item['title'],9,space=5),paragraph('Evidence: '+item['evidence'],9,space=5),paragraph('Why it matters: '+item['impact'],9,space=5),paragraph('Recommendation: '+item['recommendation'],9,space=16)])
        if not priorities:story.append(paragraph('No specific priorities were established from the available stored evidence. Agree a baseline review before selecting implementation work.',10))
        story.append(PageBreak());story.extend(section_title('Website experience','Usability, navigation and conversion opportunities on the sampled pages.'))
        profile=data['website'];lh=data['lighthouse'];performance=lh.get('performance_score');lcp=lh.get('lcp_ms')
        tech=', '.join(profile.get('technologies',[])) or 'Not identified';cms=', '.join(x for x in profile.get('technologies',[]) if any(cms in x.casefold() for cms in ['wordpress','drupal','wix','squarespace','webflow','shopify'])) or 'Not identified'
        story.append(details([('Current status','Reachable in the stored assessment'),('HTTPS',observed(profile.get('https_enabled'))),('Mobile viewport',observed(profile.get('has_viewport'))),('Mobile performance',f'{performance:g}/100 in Lighthouse' if performance is not None else 'Not assessed'),('Largest contentful paint',f'{lcp/1000:.1f} seconds' if lcp is not None else 'Not assessed'),('Contact page',observed(profile.get('has_contact_page'))),('Booking / enquiry feature',observed(profile.get('has_booking'))),('Technology / CMS',tech+' / '+cms)]))
        story.extend([Spacer(1,13),paragraph('Key website findings',13,NAVY,True),*finding_blocks(data,'WEBSITE')])
        story.append(PageBreak());story.extend(section_title('Search foundations','An evidence-based review of page structure, discovery signals and public business information.'))
        story.append(details([('Page title',profile.get('html_title') or 'Not observed'),('Meta description', 'Observed' if profile.get('meta_description') else 'Not observed'),('Primary heading',observed(profile.get('has_h1'))),('Canonical',profile.get('canonical_url') or 'Not observed'),('Robots / sitemap',observed(profile.get('has_robots_txt'))+' / '+observed(profile.get('has_sitemap'))),('Structured data',', '.join(profile.get('schema_types',[])) or 'Not observed'),('Lighthouse SEO',f"{lh['seo_score']:g}/100" if lh.get('seo_score') is not None else 'Not assessed')]))
        story.extend([Spacer(1,12),*finding_blocks(data,'SEO'),paragraph('Search positions, traffic volumes and revenue effects were not measured in this review.',8,space=8)])
        story.append(PageBreak());story.extend(section_title('Basic external security review','Passive observations of the public responses and configuration available during assessment.'))
        story.append(callout('Scope of this review','This is a passive external configuration review, not a penetration test or security certification.',colors.HexColor(KIND_COLORS['SECURITY'])))
        security=metrics['SECURITY']
        story.extend([Spacer(1,10),paragraph('Configuration score methodology',11,NAVY,True,space=5),paragraph('Each of seven checks has equal weight. A score is shown only when all seven have an explicit pass or fail. Unknown results are not treated as passes. This measures external configuration checks, not overall security or vulnerability risk.',8,space=9),details([(item['name'],{'PASS':'Observed / passed','FAIL':'Improvement required','UNKNOWN':'Not assessed'}[item['result']]) for item in security['checks']]),*finding_blocks(data,'SECURITY')])
    else:
        story.extend([Spacer(1,10),paragraph('Assessment boundary',13,NAVY,True,space=8),paragraph('Existing-site SEO and external security were not assessed. A missing assessment is not evidence of a weakness.',9,space=15)])
        if business.get('website'):story.append(details([('Listed website',business['website'])]))
        story.extend([Spacer(1,15),paragraph('A practical first step',13,NAVY,True,space=8),paragraph(scope_items(data)[0][1],10,space=15)])
    useful_social=[p for p in data.get('social_profiles',[]) if p.get('activity_status') in ('RECENT','ACTIVE','STALE')]
    if data.get('business_scale') in ('MID_MARKET','REGIONAL'):
        story.append(PageBreak());story.extend(section_title('Multi-location priorities','A coordinated improvement plan for the shared website and location-level customer journeys.'))
        story.extend([callout('Assessment boundary','The stored scores and screenshot describe the sampled website. They are not a separate audit of every branch. Confirm representative locations and shared templates before agreeing the rollout scope.'),Spacer(1,20)])
        for title,text in [
            ('Consistent experience across locations','Review shared navigation, service presentation, mobile templates and brand standards. Identify which changes can be implemented centrally and which need location-specific content.'),
            ('Accurate local information and enquiry routing','Validate the selected location pages, contact details and booking or enquiry destinations. Define ownership of updates so customers reach the appropriate team.'),
            ('Pilot, verify, then extend','Begin with representative templates and agreed locations. Compare performance and enquiry-path checks with the baseline before applying approved changes across the wider site.'),
            ('Practical governance and handover','Deliver a shared-template checklist, a scoped location-page matrix, responsibilities for ongoing updates and a repeatable post-launch audit process.')]:story.extend([paragraph(title,13,NAVY,True,space=7),paragraph(text,10,space=20)])
    if useful_social:
        story.append(PageBreak());story.extend(section_title('Public social presence','Supporting context for a consistent customer journey. Social activity does not establish commercial success.'))
        for p in useful_social[:8]:story.extend([paragraph(p['platform'].title()+' - '+p['activity_status'].title(),11,NAVY,True,space=5),paragraph(p['profile_url'],8,BLUE,space=5),paragraph(p.get('activity_reason') or 'Based on a reliably dated public post.',9,space=12)])
        story.append(paragraph('Use relevant profiles to keep contact details, brand presentation and enquiry links consistent. Unavailable activity is treated as unknown, not inactivity.',9))
    story.append(PageBreak());story.extend(section_title('Business impact','How the observed findings can affect the customer journey, without making numerical growth promises.'))
    impacts=[]
    if mode in ('NO_WEBSITE','UNREACHABLE') or (data['scores'].get('WEBSITE') or 0)>=40:impacts.append(('Enquiries and usability','A clearer, more reliable website experience may make it easier for potential customers to understand your services and take the next step.'))
    if (data['scores'].get('SEO') or 0)>=40:impacts.append(('Clarity and discoverability','Accurate page structure and business information can give visitors and search systems clearer context. Rankings or traffic gains are not guaranteed.'))
    if (data['scores'].get('SECURITY') or 0)>=40:impacts.append(('Trust and reliability','Reviewing the observed external configuration can support a more consistent experience. These observations do not establish whether a site is vulnerable or certified secure.'))
    for title,text in impacts or [('An informed starting point','A current evidence baseline can help the business decide which improvements are appropriate.')]:story.extend([paragraph(title,11,NAVY,True,space=5),paragraph(text,9,space=15)])
    story.extend([Spacer(1,12),*section_title('How PlaneByte can help','A recommended engagement based on the opportunities established in this review.')])
    for title,text in scope_items(data):story.extend([callout(title,text),Spacer(1,10)])
    story.append(PageBreak());story.extend(section_title('Recommended delivery roadmap','A proportionate implementation sequence, confirmed together after discovery.'))
    phases=[('1. Confirm and plan','Validate the recorded evidence, agree the priority pages, audience, enquiry routes and acceptance criteria.')]
    if mode in ('NO_WEBSITE','UNREACHABLE') or (data['scores'].get('WEBSITE') or 0)>=40:phases.append(('2. Build or improve the website','Deliver responsive page templates, service content structure and clear contact or booking actions. Review changes with the business owner before launch.'))
    if mode=='REACHABLE' and (data['scores'].get('SEO') or 0)>=40:phases.append(('3. Strengthen search foundations','Deliver an agreed metadata and heading plan, crawlability checks and relevant structured business information.'))
    if mode=='REACHABLE' and (data['scores'].get('SECURITY') or 0)>=40:phases.append(('4. Review external configuration','Coordinate HTTPS and the observed header settings with the hosting provider; record the verification results.'))
    phases.append(('5. Validate and hand over','Re-run the agreed checks, compare measured scores with the baseline, test enquiry routes and provide a concise handover checklist.'))
    for title,text in phases:story.extend([paragraph(title,12,NAVY,True,space=6),paragraph(text,9,space=14)])
    story.extend([Spacer(1,8),callout('Deliverables and expected outcomes','An agreed page and content plan; implementation of the scoped improvements; contact-path testing; before-and-after audit evidence; launch checklist and handover. The intended outcomes are a clearer customer journey, stronger technical foundations and measurable validation against the agreed goals.')])
    offer=data.get('offer') or {}
    if offer.get('enabled') and (mode in ('NO_WEBSITE','UNREACHABLE') or mode=='REACHABLE' and (data['scores'].get('WEBSITE') or 0)>=40):
        story.append(PageBreak());story.extend(section_title(offer.get('title','Website Redesign Launch Package'),offer.get('subtitle','Included at no additional charge with an eligible PlaneByte website project')))
        story.append(paragraph('Included services',14,NAVY,True,space=12))
        included=[]
        if offer.get('seo'):included.append(('SEO launch foundations','Page-title and description templates, core heading review and crawlability checks for the agreed website pages.'))
        if offer.get('security'):included.append(('Basic configuration review','HTTPS and agreed public security-header checks, with any hosting dependencies documented.'))
        if offer.get('support'):included.append(('Post-launch support','An agreed post-launch review, enquiry-path checks and a concise handover. The support period and limits are confirmed in the proposal.'))
        for title,text in included:
            configured_price=(offer.get('prices') or {}).get(title)
            if offer.get('show_prices') and isinstance(configured_price,str) and configured_price.strip():text+=' Configured standalone list price: '+configured_price.strip()[:80]+'. Included with the eligible website project.'
            story.extend([callout(title,text),Spacer(1,12)])
        story.extend([Spacer(1,10),paragraph('Eligibility and scope are confirmed in a written proposal. Included services apply to the agreed website project; third-party subscriptions, hosting and separately scoped work are confirmed before commitment.',9,space=20)])
    story.extend([Spacer(1,12),paragraph("Let's discuss your digital growth opportunities.",15,NAVY,True,space=9),paragraph('We can review these observations together and agree a focused, proportionate next step.',9,space=10)])
    for value in [brand.get('website'),brand.get('contact_email'),brand.get('phone')]:
        if value:story.append(paragraph(value,9,BLUE,space=4))
    doc.build(story,canvasmaker=NumberedCanvas)
    # Fixed metadata derives from the immutable report snapshot, not render time.
    from pypdf import PdfReader,PdfWriter
    reader=PdfReader(BytesIO(buffer.getvalue()));writer=PdfWriter();writer.clone_document_from_reader(reader)
    try:stamp=datetime.fromisoformat(data['created_at'].replace('Z','+00:00')).astimezone(timezone.utc).strftime("D:%Y%m%d%H%M%S+00'00'")
    except ValueError:stamp="D:20000101000000+00'00'"
    writer.add_metadata({'/Title':'Digital performance review for '+name,'/Author':'PlaneByte','/Subject':'Current website and SEO scores, configuration checks and proposed improvement targets','/CreationDate':stamp,'/ModDate':stamp})
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('wb') as file:writer.write(file)
    return output
