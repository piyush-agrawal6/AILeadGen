param([switch]$Apply)
$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
if (-not $Apply) { Write-Output 'Plan: update only the existing LeadEngine API/worker images for PlaneByte branding and client scores. Preserve IAM, secrets, limits and schema; no migration or data import.'; exit 0 }
function Checked { param([scriptblock]$Action) & $Action; if ($LASTEXITCODE -ne 0) { throw 'Brand release stopped; inspect the command result.' } }
$images=Get-Content deploy/brand-images.json -Raw | ConvertFrom-Json
Checked { gcloud run jobs update leadengine-worker --project=querryside --region=asia-south1 --image=$($images.worker) --update-env-vars="LEADENGINE_WORKER_IMAGE=$($images.worker)" --quiet }
Checked { gcloud run services update leadengine-api --project=querryside --region=asia-south1 --image=$($images.api) --no-traffic --quiet }
$revision=& gcloud run services describe leadengine-api --project=querryside --region=asia-south1 --format='value(status.latestCreatedRevisionName)'
if ($LASTEXITCODE -ne 0 -or -not $revision) { throw 'Prepared API revision not found.' }
$digest=& gcloud artifacts docker images describe $($images.api) --project=querryside --format='value(image_summary.digest)'
$deployed=& gcloud run revisions describe $revision --project=querryside --region=asia-south1 --format='value(spec.containers[0].image)'
if ($LASTEXITCODE -ne 0 -or -not $digest -or $deployed -notlike "*@$digest") { throw 'Prepared image verification failed; traffic was not changed.' }
Checked { gcloud run services update-traffic leadengine-api --project=querryside --region=asia-south1 --to-revisions="$revision=100" --quiet }
@{api=$images.api;worker=$images.worker;revision=$revision} | ConvertTo-Json | Set-Content deploy/images.json -Encoding utf8
Write-Output "PlaneByte report API ready: $revision"
