param([switch]$Apply)
$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
if (-not $Apply) { Write-Output 'Plan: build and update only the existing LeadEngine API in querryside/asia-south1; preserve identity, secrets, IAM and resource limits.'; exit 0 }
$tag=Get-Date -Format 'yyyyMMdd-HHmmss'
$image="asia-south1-docker.pkg.dev/querryside/leadengine/api:$tag"
& gcloud builds submit . --project=querryside --region=asia-south1 --config=deploy/cloudbuild.api.yaml --substitutions="_IMAGE=$image" --quiet
if ($LASTEXITCODE -ne 0) { throw 'API image build failed.' }
& gcloud run services update leadengine-api --project=querryside --region=asia-south1 --image=$image --quiet
if ($LASTEXITCODE -ne 0) { throw 'API image update failed.' }
$state=Get-Content -LiteralPath deploy/images.json -Raw | ConvertFrom-Json
$state.api=$image
$state | ConvertTo-Json | Set-Content -LiteralPath deploy/images.json -Encoding utf8
Write-Output "API updated: $image"
