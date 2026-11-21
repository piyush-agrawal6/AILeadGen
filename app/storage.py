"""Private artifact storage; callers choose typed records, never arbitrary paths."""
import mimetypes
import os
import re
import uuid
from pathlib import Path
from app.config.settings import get_settings
from app.database.prospects import now


def validate_key(key):
    if is_workspace_report(key):return key
    if not isinstance(key, str) or len(key) > 512 or not re.fullmatch(r"(?:campaigns|prospects|audits)/[A-Za-z0-9_./-]+", key) or any(segment in ("", ".", "..") for segment in key.split("/")):
        raise ValueError("Invalid artifact object key")
    return key


def is_workspace_report(key):
    if not isinstance(key,str):return False
    parts=key.split('/')
    if len(parts)!=5 or parts[0]!='workspaces' or parts[2]!='reports' or parts[4]!='report.pdf':return False
    try:return all(str(uuid.UUID(part))==part for part in (parts[1],parts[3]))
    except ValueError:return False


def workspace_report_key(org,report):
    key=f'workspaces/{org}/reports/{report}/report.pdf'
    if not is_workspace_report(key):raise ValueError('Canonical workspace and report IDs are required')
    return key


class LocalArtifactStorage:
    def __init__(self, root=Path("data/artifacts")):
        self.root = Path(root).resolve()

    def put(self, key, source, content_type):
        path = self.root / validate_key(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(Path(source).read_bytes())

    def get(self, key):
        path = self.root / validate_key(key)
        if not path.is_relative_to(self.root) or not path.is_file():
            raise FileNotFoundError("Artifact not found")
        return path.open("rb")

    def delete_many(self,keys):
        paths=[(self.root/validate_key(key)).resolve() for key in keys]
        if any(not path.is_relative_to(self.root) for path in paths):raise ValueError('Artifact path escaped storage root')
        for path in paths:path.unlink(missing_ok=True)


class R2ArtifactStorage:
    def __init__(self, client=None,*,reports=False):
        settings = get_settings()
        self.bucket = settings.reports_r2_bucket if reports else settings.r2_bucket_name
        if client is None:
            if not re.fullmatch(r'https://[a-f0-9]{32}\.r2\.cloudflarestorage\.com/?',settings.r2_endpoint):
                raise ValueError('Expected an HTTPS Cloudflare R2 account endpoint')
            key=settings.reports_r2_access_key_id.get_secret_value() if reports else settings.r2_access_key_id
            secret=settings.reports_r2_secret_access_key.get_secret_value() if reports else settings.r2_secret_access_key
            if reports and self.bucket!='planebyte-reports-prod':raise ValueError('Unexpected private reports bucket')
            if not all((self.bucket,key,secret)):
                raise ValueError('Incomplete R2 S3 configuration')
            import boto3
            from botocore.config import Config
            client = boto3.client("s3", endpoint_url=settings.r2_endpoint, aws_access_key_id=key, aws_secret_access_key=secret, region_name=settings.r2_region, config=Config(signature_version='s3v4',connect_timeout=10, read_timeout=30, retries={"mode":"standard","total_max_attempts":3}))
        self.client = client

    def put(self, key, source, content_type):
        size=Path(source).stat().st_size
        if size>64*1024*1024:raise ValueError('Artifact exceeds the upload limit')
        self.client.upload_file(str(source), self.bucket, validate_key(key), ExtraArgs={"ContentType":content_type, "CacheControl":"private, no-store"})
        info=self.stat(key)
        if info['size']!=size or info['content_type']!=content_type:
            raise IOError('Stored artifact metadata differs from upload')

    def stat(self,key):
        result=self.client.head_object(Bucket=self.bucket,Key=validate_key(key))
        return {'size':result['ContentLength'],'content_type':result['ContentType']}

    def get(self, key):
        return self.client.get_object(Bucket=self.bucket, Key=validate_key(key))["Body"]

    def delete_many(self,keys):
        keys=[validate_key(key) for key in keys]
        for start in range(0,len(keys),1000):
            result=self.client.delete_objects(Bucket=self.bucket,Delete={'Objects':[{'Key':key} for key in keys[start:start+1000]],'Quiet':True})
            if result.get('Errors'):raise RuntimeError('Some private objects could not be deleted; retry is required.')


class RoutedR2Storage:
    """The immutable key in the record, not today's feature flag, selects the read backend."""
    def put(self,key,path,content_type):
        separate=is_workspace_report(validate_key(key))
        if separate and content_type!='application/pdf':raise ValueError('Expected a PDF report')
        return R2ArtifactStorage(reports=separate).put(key,path,content_type)

    def get(self,key):return R2ArtifactStorage(reports=is_workspace_report(validate_key(key))).get(key)

    def delete_many(self,keys):
        groups={True:[],False:[]}
        for key in keys:groups[is_workspace_report(validate_key(key))].append(key)
        for separate,group in groups.items():
            if group:R2ArtifactStorage(reports=separate).delete_many(group)

def artifact_storage():
    return RoutedR2Storage() if get_settings().app_env == "production" or os.environ.get("STORAGE_BACKEND") == "r2" else LocalArtifactStorage(Path(os.environ.get("ARTIFACT_LOCAL_ROOT", "data/artifacts")))


def publish_artifact(conn, key, source, *, run_id=None, business_id=None, kind):
    content_type = mimetypes.guess_type(str(source))[0] or "application/octet-stream"
    artifact_storage().put(key, source, content_type)
    conn.execute("INSERT INTO artifact_objects(object_key,run_id,business_id,kind,content_type,created_at) VALUES(?,?,?,?,?,?) ON CONFLICT(object_key) DO UPDATE SET created_at=excluded.created_at", (validate_key(key),run_id,business_id,kind,content_type,now()))


def download_artifact(conn, *, run_id=None, business_id=None, kind):
    from fastapi.responses import StreamingResponse
    from fastapi import HTTPException
    from app.platform.context import organization
    org=organization()
    if run_id is not None:
        owned=conn.execute('SELECT 1 FROM pipeline_runs WHERE id=? AND organization_id=?',(run_id,org)).fetchone()
    else:
        owned=conn.execute('SELECT 1 FROM businesses b JOIN pipeline_runs r ON r.id=b.run_id WHERE b.id=? AND r.organization_id=?',(business_id,org)).fetchone()
    if not owned:raise HTTPException(404,'Artifact not found.')
    column, value = ("run_id",run_id) if run_id is not None else ("business_id",business_id)
    row = conn.execute(f"SELECT * FROM artifact_objects WHERE {column}=? AND kind=? ORDER BY created_at DESC LIMIT 1", (value,kind)).fetchone()
    if not row:
        return None
    try:
        body = artifact_storage().get(row["object_key"])
    except Exception:
        raise HTTPException(503, "The artifact is temporarily unavailable.")
    def chunks():
        try:
            while chunk := body.read(65536):
                yield chunk
        finally:
            body.close()
    filename = "report.html" if kind == "html" else "leads."+kind
    headers = {"Content-Disposition":f'attachment; filename="{filename}"',"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"}
    if kind == "html":
        headers["Content-Security-Policy"] = "sandbox; default-src 'none'; style-src 'unsafe-inline'"
    return StreamingResponse(chunks(), media_type=row["content_type"], headers=headers)
