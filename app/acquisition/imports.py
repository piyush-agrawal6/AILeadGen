"""Bounded server-side spreadsheets; raw rows are staged privately, never sent to AI."""
import csv,io,re,zipfile,json
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from openpyxl import load_workbook
from app.acquisition.models import ColumnMapping,ProcessingOptions
from app.config.locations import country
from app.normalization.businesses import normalize_business
from app.normalization.domains import clean_website_url
from app.database.models import Business
from app.utils.urls import is_safe_url
from app.mail.service import address as email_address

MAX_UPLOAD_BYTES=1_000_000
MAX_ROWS=10_000
MAX_COLUMNS=50
class ImportInvalid(ValueError):pass

def filename(value):
    text=Path(value.replace('\\','/')).name
    if not text or len(text)>180 or Path(text).suffix.lower() not in ('.csv','.xlsx'):raise ImportInvalid('Choose a CSV or XLSX file (up to 1 MB and 10,000 rows).')
    if any(ord(c)<32 for c in text):raise ImportInvalid('Use a normal CSV/XLSX filename.')
    return text

def headers(values):
    result=[];seen={}
    for index,value in enumerate(values):
        name=str(value or '').strip()[:120] or 'Column '+str(index+1);seen[name]=seen.get(name,0)+1
        result.append(name if seen[name]==1 else name+' ['+str(seen[name])+']')
    if not result or len(result)>MAX_COLUMNS:raise ImportInvalid('A sheet must contain 1–50 columns.')
    return result

class Spreadsheet:
    def __init__(self,raw,name):
        self.name=filename(name);self.raw=raw
        if not raw or len(raw)>MAX_UPLOAD_BYTES:raise ImportInvalid('Upload a nonempty file up to 1 MB.')
        if self.name.lower().endswith('.xlsx'):
            try:
                with zipfile.ZipFile(io.BytesIO(raw)) as z:
                    info=z.infolist()
                    if len(info)>2000 or sum(x.file_size for x in info)>25_000_000 or any(x.flag_bits&1 for x in info):raise ImportInvalid('Workbook expands beyond the safe processing limit or is encrypted.')
                    if any('vbaproject' in x.filename.casefold() for x in info):raise ImportInvalid('Macro-enabled workbooks are not supported.')
            except (zipfile.BadZipFile,OSError):raise ImportInvalid('The uploaded XLSX workbook is not valid.') from None
    @contextmanager
    def workbook(self):
        try:wb=load_workbook(io.BytesIO(self.raw),read_only=True,data_only=True,keep_links=False)
        except Exception:raise ImportInvalid('The XLSX workbook could not be read safely.') from None
        try:yield wb
        finally:wb.close()
    def rows(self,sheet=None):
        if self.name.lower().endswith('.csv'):
            try:text=self.raw.decode('utf-8-sig')
            except UnicodeDecodeError:raise ImportInvalid('Save CSV using UTF-8 encoding.') from None
            try:dialect=csv.Sniffer().sniff(text[:8192],delimiters=',;\t|')
            except csv.Error:dialect=csv.excel
            try:
                for row in csv.reader(io.StringIO(text,newline=''),dialect):yield row
            except csv.Error:raise ImportInvalid('The CSV contains malformed quoting.') from None
        else:
            with self.workbook() as wb:
                if sheet is None:sheet=wb.sheetnames[0]
                if sheet not in wb.sheetnames:raise ImportInvalid('Select a worksheet present in the workbook.')
                ws=wb[sheet]
                if ws.max_column and ws.max_column>MAX_COLUMNS:raise ImportInvalid('Select a sheet with at most 50 columns.')
                # Never trust a workbook dimension to allocate memory.
                for row in ws.iter_rows(values_only=True):yield [str(v) if v is not None else '' for v in row]
    def sheets(self):
        if self.name.lower().endswith('.csv'):return ['CSV']
        with self.workbook() as wb:
            if len(wb.sheetnames)>50:raise ImportInvalid('Workbook has too many worksheets (maximum 50).')
            return wb.sheetnames
    def inspect(self,sheet=None):
        names=self.sheets();sheet=sheet or names[0];iterator=self.rows(sheet)
        try:columns=headers(next(iterator))
        except StopIteration:raise ImportInvalid('The selected sheet is empty.') from None
        sample=[];count=0
        for row in iterator:
            if not any(str(v or '').strip() for v in row):continue
            count+=1
            if count>MAX_ROWS:raise ImportInvalid('Imports support up to 10,000 nonempty rows per sheet.')
            if len(row)>MAX_COLUMNS:raise ImportInvalid('Rows may contain at most 50 columns.')
            if any(len(str(v or ''))>4096 for v in row):raise ImportInvalid('A cell exceeds 4,096 characters; shorten it before uploading.')
            if len(sample)<5:sample.append([str(v or '')[:300] for v in row[:len(columns)]])
        return {'sheets':names,'sheet':sheet,'headers':columns,'sample':sample,'row_count':count,'file_format':'XLSX' if self.name.lower().endswith('.xlsx') else 'CSV','max_rows':MAX_ROWS,'max_upload_bytes':MAX_UPLOAD_BYTES}
    def mapped_rows(self,sheet,mapping):
        iterator=self.rows(sheet)
        try:columns=headers(next(iterator))
        except StopIteration:return
        mapping.validate_headers(columns);indices={k:columns.index(v) for k,v in mapping.model_dump().items() if v is not None}
        for number,row in enumerate(iterator,start=2):
            if not any(str(v or '').strip() for v in row):continue
            if number>MAX_ROWS+1:raise ImportInvalid('Sheet exceeds 10,000 rows.')
            yield number,{field:str(row[index] or '').strip() if index<len(row) else '' for field,index in indices.items()}

ALIASES={'hotel':'hospitality','hotels':'hospitality','hospitality':'hospitality','dentist':'dentists','dentists':'dentists','dental':'dentists','dental clinic':'dentists','restaurant':'restaurant','restaurants':'restaurant','real estate':'real_estate','real estate agency':'real_estate','estate agents':'real_estate','home services':'home_services','home service':'home_services','law':'legal','law firm':'legal','legal':'legal','veterinary':'veterinary','veterinarian':'veterinary','auto repair':'auto_repair'}
def normalize_row(data,options,source):
    data={k:str(v or '').strip() for k,v in data.items()};name=data.get('company_name','')
    if len(name)<2 or len(name)>180:raise ImportInvalid('Company name is missing or exceeds 180 characters.')
    value=data.get('website');website=None
    if value:
        website=clean_website_url(value)
        if not website or not is_safe_url(website,check_dns=False):raise ImportInvalid('Website must be a public HTTP/HTTPS address.')
    email=data.get('email')
    if email:
        try:email=email_address(email)
        except Exception:raise ImportInvalid('Email address is malformed; no address was guessed.') from None
    nation=country(data.get('country') or options.default_country)
    category=data.get('vertical','');vertical=ALIASES.get(category.casefold().replace('_',' ')) if category else options.default_vertical
    if vertical is None:
        from app.acquisition.policy import policy
        vertical=category.casefold().replace(' ','_')
    from app.config.verticals import get_vertical_manager
    definition=get_vertical_manager().resolve_vertical(vertical)
    taxonomy=next(iter(definition.overture_categories),category) if category and definition else category or None
    b=normalize_business(Business(name=name,normalized_name='',vertical=vertical,subcategory=taxonomy,country=nation.name,country_code=nation.alpha_2,city=data.get('city') or options.default_city or None,state=data.get('region') or None,address=data.get('address') or None,website=website,phone=data.get('phone') or None,public_email=email or None,source_confidence=0.6,source_category=taxonomy,source_tags=json.dumps({'acquisition_source':source,'provided_industry':category})))
    return b

def suggested_mapping(columns):
    # A transparent convenience suggestion; AI failures never masquerade as AI success.
    aliases={'company_name':['company','company name','business','organisation','organization','lead'],'website':['url','website','domain','site address'],'email':['email','mail','mail id','work email'],'phone':['phone','telephone','mobile'],'city':['city','town','market'],'country':['country'],'vertical':['industry','sector','category','type'],'contact_name':['contact person','contact name','contact'],'address':['address'],'region':['region','state']}
    return ColumnMapping(**{field:next((col for col in columns if col.casefold() in names),None) for field,names in aliases.items()})
