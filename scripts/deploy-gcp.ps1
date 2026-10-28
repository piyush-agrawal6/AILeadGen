param([string]$Project='querryside',[string]$Region='asia-south1',[switch]$Apply,[switch]$SkipProvision,[switch]$SkipBuild,[switch]$SkipMigrations)
$ErrorActionPreference='Stop'
$workspace=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $workspace
if (-not $Apply) { Write-Output "Plan: build LeadEngine API/worker, migrate additively, deploy to $Project/$Region; 2 API instances, 2 active scans, one 1-vCPU/2-GiB task per worker. Use -Apply to execute the user-approved scope."; exit 0 }
function Invoke-Checked { param([scriptblock]$Action) & $Action; if ($LASTEXITCODE -ne 0) { throw 'Deployment command failed.' } }
$deploymentEnv=@{}
Get-Content -LiteralPath (Join-Path $workspace '.env') | ForEach-Object { if ($_ -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') { $deploymentEnv[$Matches[1]]=$Matches[2].Trim().Trim('"').Trim("'") } }
if ($Project -notmatch '^[a-z][a-z0-9-]+$' -or $Region -notmatch '^[a-z]+-[a-z]+[0-9]+$') { throw 'Invalid project/region.' }
$apiIdentity="leadengine-api-sa@$Project.iam.gserviceaccount.com"
$workerIdentity="leadengine-worker-sa@$Project.iam.gserviceaccount.com"
if (-not $SkipProvision) {
foreach ($name in @('leadengine-api-sa','leadengine-worker-sa')) {
    & gcloud iam service-accounts describe "$name@$Project.iam.gserviceaccount.com" --project=$Project --format='value(email)' 2>$null
    if ($LASTEXITCODE -ne 0) { Invoke-Checked { gcloud iam service-accounts create $name --project=$Project --display-name=$name --quiet } }
}
& gcloud artifacts repositories describe leadengine --project=$Project --location=$Region --format='value(name)' 2>$null
if ($LASTEXITCODE -ne 0) { Invoke-Checked { gcloud artifacts repositories create leadengine --project=$Project --location=$Region --repository-format=docker --quiet } }
$secrets=@{DATABASE_URL='leadengine-database-url';R2_ENDPOINT='leadengine-r2-endpoint';R2_ACCESS_KEY_ID='leadengine-r2-key';R2_SECRET_ACCESS_KEY='leadengine-r2-secret';R2_BUCKET_NAME='leadengine-r2-bucket';LEADENGINE_API_SIGNING_SECRET='leadengine-api-signing';ALLOWED_USER_EMAILS='leadengine-allowed-users'}
foreach ($entry in $secrets.GetEnumerator()) {
    $value=$deploymentEnv[$entry.Key]
    if (-not $value) { throw "Missing environment key: $($entry.Key)" }
    & gcloud secrets describe $entry.Value --project=$Project --format='value(name)' 2>$null
    if ($LASTEXITCODE -ne 0) { Invoke-Checked { gcloud secrets create $entry.Value --project=$Project --replication-policy=automatic --quiet } }
    $secretFile=[IO.Path]::GetTempFileName()
    try { [IO.File]::WriteAllText($secretFile,$value,[Text.UTF8Encoding]::new($false)); Invoke-Checked { gcloud secrets versions add $entry.Value --project=$Project --data-file=$secretFile --quiet } }
    finally { Remove-Item -LiteralPath $secretFile -Force }
    $identities=@($apiIdentity)
    if ($entry.Key -notin @('LEADENGINE_API_SIGNING_SECRET','ALLOWED_USER_EMAILS')) { $identities += $workerIdentity }
    foreach ($identity in $identities) { Invoke-Checked { gcloud secrets add-iam-policy-binding $entry.Value --project=$Project --member="serviceAccount:$identity" --role=roles/secretmanager.secretAccessor --quiet } }
}
}
$buildIdentity='248535449008-compute@developer.gserviceaccount.com'
# Source read and build-log writes are bucket-scoped; no project IAM grant.
Invoke-Checked { gcloud storage buckets add-iam-policy-binding "gs://${Project}_cloudbuild" --member="serviceAccount:$buildIdentity" --role=roles/storage.objectViewer --quiet }
Invoke-Checked { gcloud storage buckets add-iam-policy-binding "gs://${Project}_cloudbuild" --member="serviceAccount:$buildIdentity" --role=roles/storage.legacyBucketReader --quiet }
& gcloud storage buckets describe "gs://$Project-leadengine-build-logs" --format='value(name)' 2>$null
if ($LASTEXITCODE -ne 0) { Invoke-Checked { gcloud storage buckets create "gs://$Project-leadengine-build-logs" --project=$Project --location=$Region --uniform-bucket-level-access --public-access-prevention --quiet } }
Invoke-Checked { gcloud storage buckets add-iam-policy-binding "gs://$Project-leadengine-build-logs" --member="serviceAccount:$buildIdentity" --role=roles/storage.objectAdmin --quiet }
Invoke-Checked { gcloud storage buckets add-iam-policy-binding "gs://$Project-leadengine-build-logs" --member="serviceAccount:$buildIdentity" --role=roles/storage.legacyBucketReader --quiet }
Invoke-Checked { gcloud artifacts repositories add-iam-policy-binding leadengine --project=$Project --location=$Region --member="serviceAccount:$buildIdentity" --role=roles/artifactregistry.writer --quiet }
$secrets=@{DATABASE_URL='leadengine-database-url';R2_ENDPOINT='leadengine-r2-endpoint';R2_ACCESS_KEY_ID='leadengine-r2-key';R2_SECRET_ACCESS_KEY='leadengine-r2-secret';R2_BUCKET_NAME='leadengine-r2-bucket';LEADENGINE_API_SIGNING_SECRET='leadengine-api-signing';ALLOWED_USER_EMAILS='leadengine-allowed-users'}
$tag=Get-Date -Format 'yyyyMMdd-HHmmss'
$apiImage="$Region-docker.pkg.dev/$Project/leadengine/api:$tag"
$workerImage="$Region-docker.pkg.dev/$Project/leadengine/worker:$tag"
if ($SkipBuild) {
    $imageState=Get-Content -LiteralPath deploy/images.json -Raw | ConvertFrom-Json
    $apiImage=$imageState.api;$workerImage=$imageState.worker
} else {
    @{api=$apiImage;worker=$workerImage} | ConvertTo-Json | Set-Content -LiteralPath deploy/images.json
    Invoke-Checked { gcloud builds submit . --project=$Project --region=$Region --config=deploy/cloudbuild.api.yaml --substitutions="_IMAGE=$apiImage" --quiet }
    Invoke-Checked { gcloud builds submit . --project=$Project --region=$Region --config=deploy/cloudbuild.worker.yaml --substitutions="_IMAGE=$workerImage" --quiet }
}
$commonEnv="APP_ENV=production,SCAN_EXECUTOR=gcp,GCP_PROJECT_ID=$Project,GCP_REGION=$Region,LEADENGINE_CLOUD_RUN_JOB=leadengine-worker,MAX_ACTIVE_SCANS=2,MAX_CITIES_PER_SCAN=10,MAX_TARGET_LEADS=1000,MAX_RAW_BUSINESSES=10000,MAX_LIGHTHOUSE_AUDITS=500,MAX_SCAN_RUNTIME_MINUTES=180"
$workerSecrets=($secrets.GetEnumerator()|Where-Object {$_.Key -notin @('LEADENGINE_API_SIGNING_SECRET','ALLOWED_USER_EMAILS')}|ForEach-Object {"$($_.Key)=$($_.Value):latest"}) -join ','
$apiSecrets=($secrets.GetEnumerator()|ForEach-Object {"$($_.Key)=$($_.Value):latest"}) -join ','
if (-not $SkipMigrations) {
Invoke-Checked { & (Join-Path $workspace '.venv/Scripts/python.exe') scripts/db_migrate.py --backend postgres }
Invoke-Checked { & (Join-Path $workspace '.venv/Scripts/python.exe') scripts/migrate_sqlite_to_postgres.py }
Invoke-Checked { & (Join-Path $workspace '.venv/Scripts/python.exe') scripts/backfill_prospects.py }
Invoke-Checked { & (Join-Path $workspace '.venv/Scripts/python.exe') scripts/migrate_artifacts.py }
}
Invoke-Checked { gcloud run jobs deploy leadengine-worker --project=$Project --region=$Region --image=$workerImage --service-account=$workerIdentity --tasks=1 --parallelism=1 --cpu=1 --memory=2Gi --max-retries=1 --task-timeout=10800s --set-env-vars="$commonEnv,LEADENGINE_ROLE=worker,LEADENGINE_WORKER_IMAGE=$workerImage" --set-secrets=$workerSecrets --quiet }
foreach ($identity in @($apiIdentity,$workerIdentity)) { Invoke-Checked { gcloud run jobs add-iam-policy-binding leadengine-worker --project=$Project --region=$Region --member="serviceAccount:$identity" --role=roles/run.jobsExecutorWithOverrides --quiet } }
Invoke-Checked { gcloud run jobs add-iam-policy-binding leadengine-worker --project=$Project --region=$Region --member="serviceAccount:$apiIdentity" --role=roles/run.viewer --quiet }
Invoke-Checked { gcloud run deploy leadengine-api --project=$Project --region=$Region --image=$apiImage --service-account=$apiIdentity --cpu=1 --memory=1Gi --min-instances=0 --max-instances=2 --concurrency=20 --timeout=300 --allow-unauthenticated --set-env-vars="$commonEnv,LEADENGINE_ROLE=api" --set-secrets=$apiSecrets --quiet }
$apiUrl=& gcloud run services describe leadengine-api --project=$Project --region=$Region --format='value(status.url)'
if ($LASTEXITCODE -ne 0) { throw 'Could not resolve deployed API URL.' }
$apiUrl | Set-Content -LiteralPath (Join-Path $workspace 'deploy/api-url.txt') -Encoding utf8
Write-Output "API deployed: $apiUrl"
