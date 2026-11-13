"""Build only committed API source, reusing the existing locked runtime/config.

The source bundle excludes frontend, local settings, credentials, customer data,
backups and large unchanged reference files. No production traffic is changed.
"""
import argparse,io,json,os,re,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CLI='/Users/planebyte/Downloads/google-cloud-sdk/bin/gcloud'
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--image-tag',default='growth-20261113-r2');args=parser.parse_args()
    if not re.fullmatch(r'growth-\d{8}-r\d{1,2}',args.image_tag):raise ValueError('Expected a bounded Growth release tag.')
    os.umask(0o077)
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    folder=ROOT/'data/artifacts/staging'/('growth-api-'+revision[:8]);folder.mkdir(parents=True,mode=0o700,exist_ok=False)
    archive=subprocess.check_output(['git','archive','--format=tar','HEAD','app','scripts'],cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as source:source.extractall(folder,filter='data')
    for name,path in [('Dockerfile','deploy/Dockerfile.growth-api'),('cloudbuild.yaml','deploy/cloudbuild.growth-api-patch.yaml')]:
        (folder/name).write_bytes(subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT))
    (folder/'.gcloudignore').write_text('__pycache__\n**/__pycache__\n*.pyc\n.env\n**/.env*\n')
    result=subprocess.run([CLI,'builds','submit',str(folder),'--project=querryside','--config='+str(folder/'cloudbuild.yaml'),'--substitutions=_IMAGE=asia-south1-docker.pkg.dev/querryside/leadengine/api:'+args.image_tag+',_SOURCE_REV='+revision,'--async','--format=json'],capture_output=True,text=True,timeout=240)
    if result.returncode:raise RuntimeError('Committed-source API patch build submission failed.')
    build=json.loads(result.stdout)
    proof=ROOT/'data/artifacts/verification'/('phase4-api-patch-'+args.image_tag+'-build.json');proof.write_text(json.dumps(build,indent=2));proof.chmod(0o600)
    print(json.dumps({'source_commit':revision,'build_id':build['id'],'status':build['status'],'source_bundle':'Committed app/scripts only; locked runtime/config reused.'}))
if __name__=='__main__':main()
