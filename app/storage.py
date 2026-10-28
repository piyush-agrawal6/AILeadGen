"""Private artifact storage; callers choose typed records, never arbitrary paths."""
import mimetypes
import os
import re
from pathlib import Path
from app.config.settings import get_settings
from app.database.prospects import now


def validate_key(key):
    if not isinstance(key, str) or len(key) > 512 or not re.fullmatch(r"(?:campaigns|prospects|audits)/[A-Za-z0-9_./-]+", key) or any(segment in ("", ".", "..") for segment in key.split("/")):
        raise ValueError("Invalid artifact object key")
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
    def __init__(self, client=None):
        settings = get_settings()
        self.bucket = settings.r2_bucket_name
        if client is None:
            import boto3
            from botocore.config import Config
            client = boto3.client("s3", endpoint_url=settings.r2_endpoint, aws_access_key_id=settings.r2_access_key_id, aws_secret_access_key=settings.r2_secret_access_key, region_name=settings.r2_region, config=Config(connect_timeout=10, read_timeout=30, retries={"max_attempts":2}))
        self.client = client

    def put(self, key, source, content_type):
        self.client.upload_file(str(source), self.bucket, validate_key(key), ExtraArgs={"ContentType":content_type, "CacheControl":"private, no-store"})

    def get(self, key):
        return self.client.get_object(Bucket=self.bucket, Key=validate_key(key))["Body"]

    def delete_many(self,keys):
        keys=[validate_key(key) for key in keys]
        for start in range(0,len(keys),1000):
            result=self.client.delete_objects(Bucket=self.bucket,Delete={'Objects':[{'Key':key} for key in keys[start:start+1000]],'Quiet':True})
            if result.get('Errors'):raise RuntimeError('Some private objects could not be deleted; retry is required.')


def artifact_storage():
    return R2ArtifactStorage() if get_settings().app_env == "production" or os.environ.get("STORAGE_BACKEND") == "r2" else LocalArtifactStorage(Path(os.environ.get("ARTIFACT_LOCAL_ROOT", "data/artifacts")))


def publish_artifact(conn, key, source, *, run_id=None, business_id=None, kind):
    content_type = mimetypes.guess_type(str(source))[0] or "application/octet-stream"
    artifact_storage().put(key, source, content_type)
    conn.execute("INSERT INTO artifact_objects(object_key,run_id,business_id,kind,content_type,created_at) VALUES(?,?,?,?,?,?) ON CONFLICT(object_key) DO UPDATE SET created_at=excluded.created_at", (validate_key(key),run_id,business_id,kind,content_type,now()))


def download_artifact(conn, *, run_id=None, business_id=None, kind):
    from fastapi.responses import StreamingResponse
    from fastapi import HTTPException
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
