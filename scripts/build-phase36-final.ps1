param([switch]$Apply)
$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
if(-not $Apply){Write-Output 'Build the existing API with full regression checks and the worker asynchronously; no live resources change.';exit 0}
$tag=Get-Date -Format 'yyyyMMdd-HHmmss'
$api="asia-south1-docker.pkg.dev/querryside/leadengine/api:phase36-validated-$tag"
$worker="asia-south1-docker.pkg.dev/querryside/leadengine/worker:phase36-validated-$tag"
.venv/Scripts/python.exe -c "from pathlib import Path;from zipfile import ZipFile,ZIP_DEFLATED;z=ZipFile('deploy/brand-validation.zip','w',ZIP_DEFLATED);[z.write(p,p.as_posix()) for p in Path('tests').rglob('*.py')];z.close()"
if($LASTEXITCODE -ne 0){throw 'Test preparation failed.'}
$apiBuild=& gcloud builds submit . --project=querryside --region=asia-south1 --config=deploy/cloudbuild.brand-api.yaml --substitutions="_IMAGE=$api" --async --quiet --format='value(id)'
if($LASTEXITCODE -ne 0){throw 'API build submission failed.'}
$workerBuild=& gcloud builds submit . --project=querryside --region=asia-south1 --config=deploy/cloudbuild.worker.yaml --substitutions="_IMAGE=$worker" --async --quiet --format='value(id)'
if($LASTEXITCODE -ne 0){throw 'Worker build submission failed.'}
@{api=$api;worker=$worker} | ConvertTo-Json | Set-Content deploy/brand-images.json -Encoding utf8
@{api=$apiBuild;worker=$workerBuild} | ConvertTo-Json | Set-Content deploy/phase36-builds.json -Encoding utf8
Write-Output 'Builds submitted. Verify both have succeeded before deployment.'
