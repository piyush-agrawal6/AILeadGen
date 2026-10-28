param([switch]$Apply)
$ErrorActionPreference='Stop'
Set-Location -LiteralPath (Split-Path $PSScriptRoot -Parent)
if(-not $Apply){Write-Output 'Deploy validated Phase 4.1 images, apply additive schema 8 and verify original rows. Preserve test mode and all secrets.';exit 0}
function Checked {param([scriptblock]$Action) &$Action;if($LASTEXITCODE -ne 0){throw 'Phase 4.1 release stopped.'}}
$configText=& .venv/Scripts/python.exe -c "import json;from app.config.settings import get_settings;s=get_settings();print(json.dumps(dict(project=s.gcp_project_id,region=s.gcp_region,worker=s.cloud_run_job)))"
if($LASTEXITCODE -ne 0){throw 'Existing deployment configuration is required.'}
$config=$configText|ConvertFrom-Json
if(-not $config.project -or -not $config.region){throw 'GCP configuration is missing.'}
if(-not (Test-Path docs/phase41-before.json)){throw 'Production baseline is required.'}
$images=Get-Content deploy/phase41-images.json -Raw|ConvertFrom-Json
$builds=Get-Content deploy/phase41-builds.json -Raw|ConvertFrom-Json
foreach($build in @($builds.api,$builds.worker)){
 $status=&gcloud builds describe $build --project=$($config.project) --region=$($config.region) --format='value(status)'
 if($LASTEXITCODE -ne 0 -or $status -ne 'SUCCESS'){throw 'Both release builds must succeed.'}
}
$before=(&gcloud run services describe leadengine-api --project=$($config.project) --region=$($config.region) --format=json)|ConvertFrom-Json
if($LASTEXITCODE -ne 0){throw 'Could not inspect current service.'}
$beforeEnv=$before.spec.template.spec.containers[0].env
$mode=($beforeEnv|Where-Object name -eq EMAIL_SEND_MODE).value
$approved=($beforeEnv|Where-Object name -eq EMAIL_LIVE_APPROVED).value
if($mode -ne 'test' -or $approved -ne 'false'){throw 'This release must preserve the current test/false sending flags.'}
$protected=@('DATABASE_URL','DATABASE_URL_UNPOOLED','AUTH_SECRET','AUTH_GOOGLE_ID','AUTH_GOOGLE_SECRET','LEADENGINE_API_SIGNING_SECRET','GCP_PROJECT_ID','GCP_REGION','R2_ACCOUNT_ID','R2_ACCESS_KEY_ID','R2_SECRET_ACCESS_KEY','R2_BUCKET_NAME','R2_ENDPOINT','MAIL_PASSWORD','EMAIL_SEND_MODE','EMAIL_LIVE_APPROVED','EMAIL_SENDING_ENABLED')
$expected=($beforeEnv|Where-Object name -in $protected|Sort-Object name|ConvertTo-Json -Depth 10 -Compress)
Checked {gcloud run services update leadengine-api --project=$($config.project) --region=$($config.region) --image=$($images.api) --no-traffic --quiet}
$revision=&gcloud run services describe leadengine-api --project=$($config.project) --region=$($config.region) --format='value(status.latestCreatedRevisionName)'
$digest=&gcloud artifacts docker images describe $images.api --project=$($config.project) --format='value(image_summary.digest)'
$deployed=&gcloud run revisions describe $revision --project=$($config.project) --region=$($config.region) --format='value(spec.containers[0].image)'
if($LASTEXITCODE -ne 0 -or -not $revision -or -not $digest -or $deployed -notlike "*@$digest"){throw 'Prepared image identity does not match.'}
Checked {.venv/Scripts/python.exe scripts/db_migrate.py --backend postgres}
Checked {.venv/Scripts/python.exe scripts/phase41_preservation.py}
Checked {gcloud run services update-traffic leadengine-api --project=$($config.project) --region=$($config.region) --to-revisions="$revision=100" --quiet}
Checked {gcloud run jobs update $config.worker --project=$($config.project) --region=$($config.region) --image=$($images.worker) --update-env-vars="LEADENGINE_WORKER_IMAGE=$($images.worker)" --quiet}
$after=(&gcloud run services describe leadengine-api --project=$($config.project) --region=$($config.region) --format=json)|ConvertFrom-Json
$actual=($after.spec.template.spec.containers[0].env|Where-Object name -in $protected|Sort-Object name|ConvertTo-Json -Depth 10 -Compress)
if($expected -cne $actual){throw 'Protected production configuration changed; inspect before proceeding.'}
@{api=$images.api;worker=$images.worker;revision=$revision;schema=8}|ConvertTo-Json|Set-Content deploy/images.json -Encoding utf8
@{api_build=$builds.api;worker_build=$builds.worker;revision=$revision;schema=8;send_mode='test';live_approved=$false;protected_configuration_preserved=$true;secret_rotation=$false}|ConvertTo-Json|Set-Content docs/phase41-deployment.json -Encoding utf8
Write-Output "Phase 4.1 release ready in test mode: $revision"
