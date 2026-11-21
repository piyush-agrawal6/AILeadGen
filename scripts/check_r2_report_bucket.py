"""Private, bounded S3 smoke. Never list buckets, enumerate customer objects or use staging."""
import hashlib
import os
import re
from uuid import uuid4

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


def verify(env):
    account=env['R2_ACCOUNT_ID'];bucket=env['R2_BUCKET'];endpoint=env['R2_ENDPOINT'].rstrip('/')
    # R2_BUCKET_NAME is the legacy artifact store. This report-only probe must never target it.
    if not re.fullmatch('[a-f0-9]{32}',account) or endpoint!=f'https://{account}.r2.cloudflarestorage.com' or bucket!='planebyte-reports-prod':
        raise ValueError('Unexpected Cloudflare production storage binding')
    client=boto3.client('s3',endpoint_url=endpoint,region_name='auto',aws_access_key_id=env['R2_ACCESS_KEY_ID'],aws_secret_access_key=env['R2_SECRET_ACCESS_KEY'],config=Config(signature_version='s3v4',connect_timeout=5,read_timeout=10,retries={'total_max_attempts':2}))
    client.head_bucket(Bucket=bucket)
    key=f'integration-tests/{uuid4()}/{uuid4()}.json';body=b'{"purpose":"synthetic storage acceptance"}'
    client.put_object(Bucket=bucket,Key=key,IfNoneMatch='*',Body=body,ContentType='application/json',CacheControl='private, no-store')
    try:
        meta=client.head_object(Bucket=bucket,Key=key)
        if meta['ContentLength']!=len(body) or meta['ContentType']!='application/json':raise RuntimeError('Metadata mismatch')
        with client.get_object(Bucket=bucket,Key=key)['Body'] as stream:
            if hashlib.sha256(stream.read(256)).digest()!=hashlib.sha256(body).digest():raise RuntimeError('Checksum mismatch')
    finally:
        client.delete_object(Bucket=bucket,Key=key)
    try:client.head_object(Bucket=bucket,Key=key)
    except ClientError as e:
        if e.response['ResponseMetadata']['HTTPStatusCode']!=404:raise
    else:raise RuntimeError('Synthetic object cleanup not verified')


if __name__=='__main__':
    verify(os.environ);print('R2 smoke passed: signed HEAD, conditional PUT, metadata, read-back, exact-key DELETE and 404.')
