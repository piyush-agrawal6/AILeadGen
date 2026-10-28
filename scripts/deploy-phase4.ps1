param([switch]$Apply)
$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
if(-not $Apply){Write-Output 'Prepare the validated existing API/worker, apply additive schema 7, verify data preservation and route API traffic. No discovery or reset.';exit 0}
function Checked {param([scriptblock]$Action) &$Action;if($LASTEXITCODE -ne 0){throw 'Phase 4 deployment stopped.'}}
$images=Get-Content deploy/brand-images.json -Raw | ConvertFrom-Json
Checked {gcloud run jobs update leadengine-worker --project=querryside --region=asia-south1 --image=$($images.worker) --update-env-vars="LEADENGINE_WORKER_IMAGE=$($images.worker)" --quiet}
Checked {gcloud run services update leadengine-api --project=querryside --region=asia-south1 --image=$($images.api) --no-traffic --quiet}
$revision=&gcloud run services describe leadengine-api --project=querryside --region=asia-south1 --format='value(status.latestCreatedRevisionName)'
$digest=&gcloud artifacts docker images describe $($images.api) --project=querryside --format='value(image_summary.digest)'
$deployed=&gcloud run revisions describe $revision --project=querryside --region=asia-south1 --format='value(spec.containers[0].image)'
if(-not $revision -or -not $digest -or $deployed -notlike "*@$digest"){throw 'Prepared image does not match validated release.'}
Checked {.venv/Scripts/python.exe scripts/db_migrate.py --backend postgres}
Checked {.venv/Scripts/python.exe scripts/phase4_preservation.py}
Checked {gcloud run services update-traffic leadengine-api --project=querryside --region=asia-south1 --to-revisions="$revision=100" --quiet}
@{api=$images.api;worker=$images.worker;revision=$revision;schema=7}|ConvertTo-Json|Set-Content deploy/images.json -Encoding utf8
Write-Output "Phase 4 API ready: $revision"
