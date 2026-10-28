param([switch]$Apply)
$ErrorActionPreference='Stop'
$workspace=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $workspace
if (-not $Apply) { Write-Output 'Plan: build and update only the existing LeadEngine worker job in querryside/asia-south1; preserve identity, secrets, task count and resource limits.'; exit 0 }
$tag=Get-Date -Format 'yyyyMMdd-HHmmss'
$image="asia-south1-docker.pkg.dev/querryside/leadengine/worker:$tag"
& gcloud builds submit . --project=querryside --region=asia-south1 --config=deploy/cloudbuild.worker.yaml --substitutions="_IMAGE=$image" --quiet
if ($LASTEXITCODE -ne 0) { throw 'Worker image build failed.' }
& gcloud run jobs update leadengine-worker --project=querryside --region=asia-south1 --image=$image --update-env-vars="LEADENGINE_WORKER_IMAGE=$image" --quiet
if ($LASTEXITCODE -ne 0) { throw 'Worker job update failed.' }
$state=Get-Content -LiteralPath deploy/images.json -Raw | ConvertFrom-Json
$state.worker=$image
$state | ConvertTo-Json | Set-Content -LiteralPath deploy/images.json -Encoding utf8
Write-Output "Worker updated: $image"
