param([switch]$Apply,[switch]$SkipBuild,[switch]$BuildOnly)
$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
if (-not $Apply) { Write-Output 'Plan: build existing API and worker; update worker, prepare API without traffic, apply only schema migration 5, then switch API traffic. Preserve IAM, secrets, identities and resource limits.'; exit 0 }
function Checked { param([scriptblock]$Action) & $Action; if ($LASTEXITCODE -ne 0) { throw 'Phase 3.5 release stopped; inspect the preceding command.' } }
if (-not $SkipBuild) {
 $tag=Get-Date -Format 'yyyyMMdd-HHmmss'
 $apiImage="asia-south1-docker.pkg.dev/querryside/leadengine/api:phase35-$tag"
 $workerImage="asia-south1-docker.pkg.dev/querryside/leadengine/worker:phase35-$tag"
 @{api=$apiImage;worker=$workerImage} | ConvertTo-Json | Set-Content -LiteralPath deploy/phase35-images.json -Encoding utf8
 Checked { gcloud builds submit . --project=querryside --region=asia-south1 --config=deploy/cloudbuild.api.yaml --substitutions="_IMAGE=$apiImage" --quiet }
 Checked { gcloud builds submit . --project=querryside --region=asia-south1 --config=deploy/cloudbuild.worker.yaml --substitutions="_IMAGE=$workerImage" --quiet }
} else { $state=Get-Content deploy/phase35-images.json -Raw | ConvertFrom-Json; $apiImage=$state.api; $workerImage=$state.worker }
if ($BuildOnly) { Write-Output "Phase 3.5 images built."; exit 0 }
Checked { gcloud run jobs update leadengine-worker --project=querryside --region=asia-south1 --image=$workerImage --update-env-vars="LEADENGINE_WORKER_IMAGE=$workerImage" --quiet }
Checked { gcloud run services update leadengine-api --project=querryside --region=asia-south1 --image=$apiImage --no-traffic --quiet }
$revision=& gcloud run services describe leadengine-api --project=querryside --region=asia-south1 --format='value(status.latestCreatedRevisionName)'
if ($LASTEXITCODE -ne 0 -or -not $revision) { throw 'Could not verify the prepared API revision.' }
$expectedDigest=& gcloud artifacts docker images describe $apiImage --project=querryside --format='value(image_summary.digest)'
$revisionImage=& gcloud run revisions describe $revision --project=querryside --region=asia-south1 --format='value(spec.containers[0].image)'
if ($LASTEXITCODE -ne 0 -or -not $expectedDigest -or $revisionImage -notlike "*@$expectedDigest") { throw 'Prepared API revision does not match the release image; traffic was not changed.' }

# The new API and scan worker accept schemas 4 and 5 during this brief rollout.
# No data import, backfill, artifact migration, or production deletion occurs.
Checked { .venv/Scripts/python.exe scripts/db_migrate.py --backend postgres }
Checked { gcloud run services update-traffic leadengine-api --project=querryside --region=asia-south1 --to-revisions="$revision=100" --quiet }
@{api=$apiImage;worker=$workerImage;revision=$revision} | ConvertTo-Json | Set-Content -LiteralPath deploy/images.json -Encoding utf8
Write-Output "Phase 3.5 API ready: $revision"
