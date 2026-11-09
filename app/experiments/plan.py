from datetime import date
EXPERIMENT_ID='planebyte-2026-11-02-06'
NAME='PlaneByte 5-Day Outreach Experiment — Nov 2–6, 2026'
START='2026-11-02';END='2026-11-06';DAILY_TARGET=500;TOTAL_TARGET=2500
TEMPLATES=('AEO_READINESS','LOCAL_AEO','CYBER_AUDIT','AEO_CYBER','THREE_FINDINGS')
MARKETS=[
 [('Austin','United States','hospitality'),('Miami','United States','dentists'),('Manchester','United Kingdom','legal'),('Toronto','Canada','real_estate'),('Sydney','Australia','home_services')],
 [('Denver','United States','dentists'),('Tampa','United States','legal'),('Birmingham','United Kingdom','real_estate'),('Vancouver','Canada','home_services'),('Melbourne','Australia','hospitality')],
 [('Charlotte','United States','legal'),('Phoenix','United States','real_estate'),('Leeds','United Kingdom','home_services'),('Calgary','Canada','hospitality'),('Brisbane','Australia','dentists')],
 [('Nashville','United States','real_estate'),('San Diego','United States','home_services'),('Bristol','United Kingdom','hospitality'),('Ottawa','Canada','dentists'),('Perth','Australia','legal')],
 [('Raleigh','United States','home_services'),('Houston','United States','hospitality'),('Liverpool','United Kingdom','dentists'),('Edmonton','Canada','legal'),('Adelaide','Australia','real_estate')]]
ZONES={'Austin':'America/Chicago','Miami':'America/New_York','Manchester':'Europe/London','Toronto':'America/Toronto','Sydney':'Australia/Sydney','Denver':'America/Denver','Tampa':'America/New_York','Birmingham':'Europe/London','Vancouver':'America/Vancouver','Melbourne':'Australia/Melbourne','Charlotte':'America/New_York','Phoenix':'America/Phoenix','Leeds':'Europe/London','Calgary':'America/Edmonton','Brisbane':'Australia/Brisbane','Nashville':'America/Chicago','San Diego':'America/Los_Angeles','Bristol':'Europe/London','Ottawa':'America/Toronto','Perth':'Australia/Perth','Raleigh':'America/New_York','Houston':'America/Chicago','Liverpool':'Europe/London','Edmonton':'America/Edmonton','Adelaide':'Australia/Adelaide'}
def segments():
 return [{'day':n+1,'date':f'2026-11-{n+2:02}','city':city,'country':country,'vertical':vertical,'target':100,'sources':{'OVERTURE':50,'FIRECRAWL':50},'timezone':ZONES[city]} for n,rows in enumerate(MARKETS) for city,country,vertical in rows]
def in_window(at,timezone):
 from zoneinfo import ZoneInfo
 local=at.astimezone(ZoneInfo(timezone));return local.weekday()<5 and '09:30'<=local.strftime('%H:%M')<'16:30'
