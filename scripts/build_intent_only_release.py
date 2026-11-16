"""Build exact committed source on the existing locked backend runtimes."""
import io,json,os,subprocess,tarfile
from pathlib import Path
from scripts.deploy_beta_backend import CLI
ROOT=Path(__file__).resolve().parents[1]
def main():
    os.umask(0o077);revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    folder=ROOT/'data/artifacts/staging'/('intent-only-'+revision[:10]);folder.mkdir(parents=True,exist_ok=False,mode=0o700)
    with tarfile.open(fileobj=io.BytesIO(subprocess.check_output(['git','archive','--format=tar','HEAD','app','scripts'],cwd=ROOT))) as source:source.extractall(folder,filter='data')
    for name,path in [('Dockerfile.api','deploy/Dockerfile.billing-api'),('Dockerfile.worker','deploy/Dockerfile.billing-worker'),('cloudbuild.yaml','deploy/cloudbuild.billing-patch.yaml')]:
        (folder/name).write_bytes(subprocess.check_output(['git','show','HEAD:'+path],cwd=ROOT))
    (folder/'.gcloudignore').write_text('__pycache__\n**/__pycache__\n*.pyc\n.env\n**/.env*\n')
    api='asia-south1-docker.pkg.dev/querryside/leadengine/api:intent-only-'+revision[:10]
    worker='asia-south1-docker.pkg.dev/querryside/leadengine/worker:intent-only-'+revision[:10]
    p=subprocess.run([CLI,'builds','submit',str(folder),'--project=querryside','--config='+str(folder/'cloudbuild.yaml'),'--substitutions=_API_IMAGE='+api+',_WORKER_IMAGE='+worker+',_SOURCE_REV='+revision,'--async','--format=json'],capture_output=True,text=True,timeout=240)
    if p.returncode:raise RuntimeError('Backend build submission failed; credentials withheld.')
    build=json.loads(p.stdout);proof={'source_commit':revision,'build_id':build['id'],'api_image':api,'worker_image':worker,'status':build['status']}
    file=ROOT/'data/artifacts/verification/intent-only/build.json';file.parent.mkdir(parents=True,exist_ok=True);file.write_text(json.dumps(proof,indent=2));file.chmod(0o600);print(json.dumps(proof))
if __name__=='__main__':main()
