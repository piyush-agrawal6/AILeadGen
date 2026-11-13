"""Read-only outgoing Git blob inventory and presence-only credential match scan."""
import argparse
import json
import re
import subprocess
from pathlib import Path
from dotenv import dotenv_values

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--base',default='origin/main');parser.add_argument('--report');parser.add_argument('--index',action='store_true');args=parser.parse_args()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
head=git('rev-parse','HEAD').decode().strip();base=git('rev-parse',args.base).decode().strip()
objects=git('rev-list','--objects',args.base+'..HEAD').decode().splitlines()
oids=[line.split(' ',1)[0] for line in objects]
result=subprocess.run(['git','cat-file','--batch-check=%(objectname) %(objecttype) %(objectsize)'],input='\n'.join(oids)+'\n',capture_output=True,text=True,cwd=ROOT,check=True)
sizes={parts[0]:int(parts[2]) for line in result.stdout.splitlines() if len(parts:=line.split())==3 and parts[1]=='blob'}
paths={line.split(' ',1)[0]:line.split(' ',1)[1] for line in objects if ' ' in line}
large=[{'oid':oid,'bytes':size,'path':paths.get(oid,'')} for oid,size in sizes.items() if size>=50*1024*1024]
tree=git('ls-tree','-r','-z','HEAD')
if args.index:
    normalized=[]
    for row in git('ls-files','--stage','-z').split(b'\0'):
        if row:
            metadata,name=row.split(b'\t',1);mode,oid,stage=metadata.split()
            if stage!=b'0':raise ValueError('Unmerged index cannot be released.')
            normalized.append(mode+b' blob '+oid+b'\t'+name)
    tree=b'\0'.join(normalized)
generated=[];private=[];secrets=[]
values={}
for path in [ROOT/'.env',ROOT/'dashboard/.env.local',ROOT/'dashboard/.env']:
    if path.is_file():
        values.update({k:v for k,v in dotenv_values(path,interpolate=False).items() if v and len(v)>=16 and re.search(r'SECRET|PASSWORD|TOKEN|(?:^|_)KEY$|DATABASE_URL',k)})
for row in tree.split(b'\0'):
    if not row:continue
    metadata,name=row.split(b'\t',1);name=name.decode();oid=metadata.decode().split()[2]
    pieces=Path(name).parts
    if any(p.startswith('.next') and p!='next-env.d.ts' for p in pieces) or any(p in ('node_modules','playwright-report','test-results','__pycache__','.venv') for p in pieces):generated.append(name);continue
    if name.startswith(('data/backups/','data/artifacts/','data/e2e/')) or name.endswith(('.db','.sqlite','.sqlite3','.pem','.p12','.key','.pack','.zip','.tar.gz')) or any(p.startswith('.env') and p!='.env.example' for p in pieces):private.append(name);continue
    if sizes.get(oid,0)>2*1024*1024:continue
    if not name.endswith(('.py','.ts','.tsx','.json','.yaml','.yml','.md','.txt','.sh','.ps1','.toml','.example')):continue
    data=git('cat-file','blob',oid)
    matched=[key for key,value in values.items() if value.encode() in data]
    if matched:secrets.append({'path':name,'matching_variable_names':matched})
# Scan every outgoing version too: removing a secret in a later commit does
# not remove it from the object set that GitHub will receive.
for oid,size in sizes.items():
    if size>2*1024*1024:continue
    data=git('cat-file','blob',oid)
    matched=[key for key,value in values.items() if value.encode() in data]
    if matched and not any(row.get('oid')==oid for row in secrets):secrets.append({'path':paths.get(oid,''),'oid':oid,'matching_variable_names':matched,'scope':'outgoing_history'})
report={'head':head,'remote_tracking_base':base,'outgoing_objects':len(objects),'oversized_blobs':large,
    'generated_tracked_paths':generated,'private_or_artifact_paths':private,'current_credential_matches':secrets,'values_disclosed':False,'index_scanned':args.index}
if args.report:
    target=Path(args.report).resolve();base_dir=Path('/var/folders/59/jbvs2d7j0yb1229glt7v904c0000gn/T/opencode').resolve()
    if not target.is_relative_to(base_dir) or target.exists():raise ValueError('Fresh approved temporary report required.')
    target.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({**{k:v for k,v in report.items() if k not in ('generated_tracked_paths','private_or_artifact_paths')},'generated_tracked_count':len(generated),'private_artifact_count':len(private),'report':str(target)},indent=2))
else:print(json.dumps(report,indent=2))
