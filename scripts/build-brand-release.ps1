param([switch]$Apply)
$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
if (-not $Apply) { Write-Output 'Plan: build the revised existing API/worker and run offline API/PDF tests inside the Linux API image. No live resources or permissions are changed.'; exit 0 }
$tag=Get-Date -Format 'yyyyMMdd-HHmmss'
$api="asia-south1-docker.pkg.dev/querryside/leadengine/api:brand-$tag"
$worker="asia-south1-docker.pkg.dev/querryside/leadengine/worker:brand-$tag"
@{api=$api;worker=$worker} | ConvertTo-Json | Set-Content deploy/brand-images.json -Encoding utf8
& .venv/Scripts/python.exe -c "from pathlib import Path;from zipfile import ZipFile,ZIP_DEFLATED;z=ZipFile('deploy/brand-validation.zip','w',ZIP_DEFLATED);[z.write(p,p.as_posix()) for p in Path('tests').rglob('*.py')];z.close()"
if ($LASTEXITCODE -ne 0) { throw 'Could not prepare offline validation sources.' }
& gcloud builds submit . --project=querryside --region=asia-south1 --config=deploy/cloudbuild.brand-api.yaml --substitutions="_IMAGE=$api" --quiet
if ($LASTEXITCODE -ne 0) { throw 'API build or regression validation failed.' }
& gcloud builds submit . --project=querryside --region=asia-south1 --config=deploy/cloudbuild.worker.yaml --substitutions="_IMAGE=$worker" --quiet
if ($LASTEXITCODE -ne 0) { throw 'Worker build failed.' }
Write-Output 'Revised images built and Linux regression tests passed.'
