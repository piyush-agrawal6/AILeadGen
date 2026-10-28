import re
from app.database.prospects import now

SEEDS=[
 ('website','Website redesign','Website','A focused website review for {{business_name}}','Hello,\n\nI reviewed the available public website evidence for {{business_name}}. {{top_finding}}\n\nPlaneByte can help prioritise a clearer customer journey and a focused website improvement plan. Would a short discussion be useful?'),
 ('no-website','No website','Website','A website starting point for {{business_name}}','Hello,\n\nAn official website was not found in the public sources sampled for {{business_name}}. If you already have one, please point me to the correct address. Otherwise, PlaneByte can help plan a clear site for your services and enquiries.\n\nWould it be useful to discuss an initial scope?'),
 ('unreachable','Website unreachable','Website','A website access observation for {{business_name}}','Hello,\n\nThe listed website for {{business_name}} did not respond successfully during our stored assessment. This may have been temporary. PlaneByte can help review the intended domain and discuss recovery or a focused redesign if appropriate.\n\nWould a brief conversation be useful?'),
 ('seo','SEO opportunity','SEO','Search foundations for {{business_name}}','Hello,\n\nOur sampled website review for {{business_name}} recorded this observation: {{top_finding}}\n\nPlaneByte can help review the relevant page structure and technical search foundations. We would validate the scope together before recommending changes.\n\nMay I share the recorded audit with you?'),
 ('local-seo','Local SEO opportunity','SEO','Local website information for {{business_name}}','Hello,\n\nI am reaching out about the public website information for {{business_name}}. {{top_finding}}\n\nPlaneByte can help review accurate business details and useful service/location content for your actual service area. Would a short review be useful?'),
 ('security','Basic security opportunity','Security','Public configuration review for {{business_name}}','Hello,\n\nOur passive public website review recorded the following configuration observation for {{business_name}}: {{top_finding}}\n\nThis is not a penetration test or a claim that the site is compromised. PlaneByte can help review the specific settings with your website provider. Would you like to discuss the findings?'),
 ('mid-market','Mid-market modernization','General','A coordinated website review for {{business_name}}','Hello,\n\nPlaneByte helps businesses plan consistent website templates, location information and enquiry journeys. For {{business_name}}, our sampled review recorded: {{top_finding}}\n\nWe could validate representative pages and agree a phased improvement scope rather than assuming every location needs the same work. Would a short discussion be useful?'),
 ('followup-1','Follow-up 1','General','Following up: {{business_name}}','Hello,\n\nI wanted to follow up on the website observations I shared for {{business_name}}. If this is relevant, I would be happy to discuss a practical next step. If the timing is not right, please let me know.'),
 ('followup-2','Follow-up 2','General','Website review for {{business_name}}','Hello,\n\nChecking once more whether the review for {{business_name}} would be useful to discuss. There is no urgency; I am happy to work around your priorities.'),
 ('no-response','After no response','General','Closing the loop: {{business_name}}','Hello,\n\nI will close the loop on my earlier note for {{business_name}}. If you would like to revisit the observations later, please feel free to reply. Thank you for your time.'),
 ('after-meeting','After meeting','General','Next steps for {{business_name}}','Hello,\n\nThank you for the conversation. I would be happy to confirm the scope, responsibilities and practical next steps for {{business_name}}. Please let me know any priorities you would like reflected in the proposal.')]

VARIABLES={'business_name','website','city','vertical','primary_opportunity','top_finding','sender_name','sender_company'}
def seed(c):
    for key,name,category,subject,body in SEEDS:c.execute('INSERT INTO email_templates(id,name,category,subject,body_text,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT DO NOTHING',(key,name,category,subject,body,now()))
def render(text,values):
    unknown=set(re.findall(r'{{\s*([\w]+)\s*}}',text))-VARIABLES
    if unknown:raise ValueError('Unsupported template variable')
    return re.sub(r'{{\s*([\w]+)\s*}}',lambda m:str(values.get(m[1]) or ''),text).strip()
