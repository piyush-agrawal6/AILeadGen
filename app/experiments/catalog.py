"""Optional owner-supplied catalog; snapshots apply only to newly prepared messages."""
import hashlib,json
from app.database.prospects import now

def status(c):
 row=c.execute('SELECT * FROM experiment_catalog WHERE id=1').fetchone()
 return dict(row) if row else {'version':0,'status':'NOT_CONFIGURED','attach_enabled':0,'mode':'BRIEF_ONLY','object_key':None,'public_url':None,'filename':None,'size_bytes':0}

def snapshot(c):
 s=status(c)
 if not s['attach_enabled'] or (s['status']!='CONFIGURED' and not(s['mode']=='CATALOG_LINK' and s.get('public_url'))):return {'mode':'BRIEF_ONLY','catalog_attached':False}
 if s['mode']=='CATALOG_LINK':
  from app.reports.data import public_url
  if not public_url(s.get('public_url')):return {'mode':'BRIEF_ONLY','catalog_attached':False}
 return {k:s.get(k) for k in ('version','mode','object_key','filename','sha256','size_bytes','public_url')}|{'catalog_attached':s['mode']=='BRIEF_PLUS_CATALOG'}

def upload(c,raw,actor):
 from io import BytesIO
 from pathlib import Path
 from tempfile import NamedTemporaryFile
 from pypdf import PdfReader
 from app.storage import artifact_storage
 if not raw.startswith(b'%PDF-') or len(raw)>4_000_000:raise ValueError('Choose a PDF up to4MB.')
 reader=PdfReader(BytesIO(raw))
 if reader.is_encrypted or not 1<=len(reader.pages)<=100:raise ValueError('Choose an unencrypted catalog up to100pages.')
 old=status(c);version=old['version']+1;digest=hashlib.sha256(raw).hexdigest();key=f'prospects/planebyte/catalog/v{version}-{digest[:12]}.pdf'
 with NamedTemporaryFile(suffix='.pdf') as f:f.write(raw);f.flush();artifact_storage().put(key,Path(f.name),'application/pdf')
 c.execute("INSERT INTO experiment_catalog(id,version,status,object_key,filename,sha256,size_bytes,attach_enabled,mode,updated_at,updated_by) VALUES(1,?,'CONFIGURED',?,'PlaneByte Product Catalog.pdf',?,?,0,'BRIEF_ONLY',?,?) ON CONFLICT(id) DO UPDATE SET version=excluded.version,status=excluded.status,object_key=excluded.object_key,filename=excluded.filename,sha256=excluded.sha256,size_bytes=excluded.size_bytes,updated_at=excluded.updated_at,updated_by=excluded.updated_by",(version,key,digest,len(raw),now(),actor))
 return status(c)
