"""One versioned company introduction. Never receives prospect data."""
from pathlib import Path
from html import escape
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from app.reports.pdf import fonts,mark,PAGE_W,PAGE_H

ORANGE=colors.HexColor('#F4511E');INK=colors.HexColor('#18212C');MUTED=colors.HexColor('#5B6572');LINE=colors.HexColor('#E5E8EB');PALE=colors.HexColor('#F6F7F8')

def generate(path):
 fonts();Path(path).parent.mkdir(parents=True,exist_ok=True);c=canvas.Canvas(str(path),pagesize=(PAGE_W,PAGE_H),pageCompression=1,invariant=1);c.setTitle('PlaneByte - Capabilities & Services');c.setAuthor('PlaneByte');w=PAGE_W-104
 def text(value,x,y,width=w,size=12,color=INK,bold=False,max_height=200):
  p=Paragraph(escape(value).replace('\n','<br/>'),ParagraphStyle('pb',fontName='PBBold' if bold else 'PBRegular',fontSize=size,leading=size*1.36,textColor=color))
  _,h=p.wrap(width,1000)
  if h>max_height:raise ValueError('Company PDF content exceeds reviewed layout.')
  p.drawOn(c,x,y-h);return y-h
 def base(n,label):
  c.setFillColor(colors.white);c.rect(0,0,PAGE_W,PAGE_H,fill=1,stroke=0);mark(c,52,PAGE_H-83,34);text('PlaneByte',98,PAGE_H-55,size=13,bold=True);text('CAPABILITIES & SERVICES',98,PAGE_H-73,size=7,color=MUTED)
  c.setStrokeColor(LINE);c.line(52,54,PAGE_W-52,54);text('planebyte.com',52,40,size=8,color=MUTED);text(f'{label}   /   {n:02}',PAGE_W-206,40,width=154,size=8,color=MUTED);c.linkURL('https://planebyte.com',(52,24,155,45),relative=0)
 def eyebrow(label,y):text(label.upper(),52,y,size=9,color=ORANGE,bold=True)
 def card(x,y,width,title,body,height=156):
  c.setFillColor(PALE);c.roundRect(x,y-height,width,height,8,fill=1,stroke=0);text(title,x+17,y-18,width=width-34,size=10,color=ORANGE,bold=True);text(body,x+17,y-42,width=width-34,size=11,max_height=height-48)
 base(1,'INTRODUCTION');eyebrow('Build new. Improve existing.',PAGE_H-124)
 text('PlaneByte',52,PAGE_H-153,size=55,bold=True)
 text('Software Engineering · Cloud · Cybersecurity\nSearch Visibility',52,PAGE_H-232,size=12,color=MUTED,max_height=46)
 text('We build new digital products -\nand improve the ones businesses\nalready rely on.',52,PAGE_H-310,size=27,bold=True,max_height=140)
 text('PlaneByte is a software and technology studio helping businesses build, debug, maintain, secure, scale and improve digital systems.\n\nOur work spans software engineering, cloud operations, cybersecurity and modern search visibility.',52,PAGE_H-454,size=14,max_height=160)
 card(52,199,w,'A PRACTICAL TECHNICAL PARTNER','From a new product to an existing production problem, we can help define the work and implement the improvements.',height=101)
 text('planebyte.com   ·   contact@planebyte.com',52,82,size=10,color=MUTED)
 c.linkURL('mailto:contact@planebyte.com',(151,65,370,87),relative=0);c.showPage()
 base(2,'OUR SERVICES');eyebrow('What we do',PAGE_H-123);text('Across the digital lifecycle.',52,PAGE_H-149,size=28,bold=True)
 gap=16;col=(w-gap)/2;top=PAGE_H-215
 card(52,top,col,'BUILD','Custom software · Web applications\nMobile & desktop applications\nWebsites · SaaS products\nInternal tools · APIs & backends\nAI integrations & automation',height=166)
 card(52+col+gap,top,col,'FIX & IMPROVE','Debugging & bug fixing\nMaintenance & feature development\nPerformance & code improvements\nLegacy modernization\nProduction troubleshooting',height=166)
 top-=183
 card(52,top,col,'CLOUD & OPERATIONS','AWS · Google Cloud · Azure\nDeployment & migration\nDevOps · Docker · CI/CD\nInfrastructure & scaling\nMonitoring & troubleshooting',height=162)
 card(52+col+gap,top,col,'SECURITY','Security audits & VAPT\nPenetration testing\nApplication & cloud security\nConfiguration review & hardening\nRemediation',height=162)
 top-=179
 card(52,top,w,'SEARCH VISIBILITY','SEO · Technical SEO · Local SEO\nAEO · GEO · AI-search visibility\nStructured data & search-ready content architecture',height=129)
 text('Scope is agreed around the business requirement. Not every project needs every service.',52,91,size=9,color=MUTED,max_height=30);c.showPage()
 base(3,'WORK WITH US');eyebrow('The PlaneByte difference',PAGE_H-123)
 text('One technical partner\nacross the full system.',52,PAGE_H-151,size=31,bold=True,max_height=100)
 text('Many projects require more than development alone. PlaneByte combines engineering, maintenance, cloud operations, cybersecurity and search visibility within one team.',52,PAGE_H-258,size=13,max_height=80)
 y=PAGE_H-350
 for title,body in [('PRODUCTION & PERFORMANCE','A production issue may involve application code, cloud infrastructure and performance. We can work across those layers.'),('SEARCH & DISCOVERY','A visibility problem may require both technical product changes and SEO, AEO or GEO improvements.'),('SECURITY & REMEDIATION','A security review is more valuable when the same engineering team can also help implement the remediation.')]:
  card(52,y,w,title,body,height=92);y-=104
 text('BUILD   /   FIX   /   MAINTAIN   /   SECURE   /   SCALE   /   GET DISCOVERED',52,175,size=8,color=ORANGE,bold=True)
 text('Have a project, existing technical problem, security requirement or search-visibility goal?',52,151,size=11,max_height=40)
 text('Talk to PlaneByte.',52,110,size=17,bold=True)
 text('planebyte.com   ·   contact@planebyte.com',52,80,size=10,color=MUTED)
 c.linkURL('https://planebyte.com',(52,63,148,88),relative=0);c.linkURL('mailto:contact@planebyte.com',(154,63,380,88),relative=0)
 c.linkURL('https://planebyte.com/projects',(PAGE_W-190,63,PAGE_W-52,88),relative=0);text('Explore our projects →',PAGE_W-190,80,width=138,size=9,color=ORANGE)
 c.showPage();c.save();return Path(path)

if __name__=='__main__':generate('output/pdf/planebyte-capabilities-v1.pdf')
