param([switch]$Apply)
$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
if(-not $Apply){Write-Output 'Release validated Phase 4 API and worker images. No migrations, discovery, data reset, or secret changes.';exit 0}
function Checked {param([scriptblock]$Action) &$Action;if($LASTEXITCODE -ne 0){throw 'Phase 4 mail release stopped.'}}
$configText=& .venv/Scripts/python.exe -c "import json;from app.config.settings import get_settings;s=get_settings();print(json.dumps(dict(project=s.gcp_project_id,region=s.gcp_region,worker=s.cloud_run_job)))"
if($LASTEXITCODE -ne 0){throw 'Could not read existing deployment configuration.'}
$config=$configText | ConvertFrom-Json
if(-not $config.project -or -not $config.region -or -not $config.worker){throw 'Existing GCP configuration is required.'}
$images=Get-Content deploy/brand-images.json -Raw | ConvertFrom-Json
$builds=Get-Content deploy/phase4-builds.json -Raw | ConvertFrom-Json
foreach($build in @($builds.api,$builds.worker)){
 $status=& gcloud builds describe $build --project=$($config.project) --region=$($config.region) --format='value(status)'
 if($LASTEXITCODE -ne 0 -or $status -ne 'SUCCESS'){throw 'Both release builds must succeed before rollout.'}
}
Checked {gcloud run jobs update $config.worker --project=$($config.project) --region=$($config.region) --image=$($images.worker) --update-env-vars="LEADENGINE_WORKER_IMAGE=$($images.worker)" --quiet}
Checked {gcloud run services update leadengine-api --project=$($config.project) --region=$($config.region) --image=$($images.api) --no-traffic --quiet}
$revision=& gcloud run services describe leadengine-api --project=$($config.project) --region=$($config.region) --format='value(status.latestCreatedRevisionName)'
$digest=& gcloud artifacts docker images describe $images.api --project=$($config.project) --format='value(image_summary.digest)'
$deployed=& gcloud run revisions describe $revision --project=$($config.project) --region=$($config.region) --format='value(spec.containers[0].image)'
if($LASTEXITCODE -ne 0 -or -not $revision -or -not $digest -or $deployed -notlike "*@$digest"){throw 'Prepared image does not match validated release.'}
Checked {gcloud run services update-traffic leadengine-api --project=$($config.project) --region=$($config.region) --to-revisions="$revision=100" --quiet}
@{api=$images.api;worker=$images.worker;revision=$revision;schema=7}|ConvertTo-Json|Set-Content deploy/images.json -Encoding utf8
@{api_build=$builds.api;worker_build=$builds.worker;revision=$revision;test_mode=$true;secrets_changed=$false;migrations_run=$false}|ConvertTo-Json|Set-Content docs/phase4-reply-fix-deployment.json -Encoding utf8
Write-Output "Phase 4 mail release ready: $revision"
