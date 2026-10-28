param([string]$Scope='piyushagrawal6s-projects',[string]$ProjectName='leadengine',[string]$ApiUrl='',[switch]$Apply)
$ErrorActionPreference='Stop'
if (-not $Apply) { Write-Output 'Plan: configure server-only auth/API variables and deploy the LeadEngine dashboard on Node 24. Use -Apply to execute the user-approved scope.'; exit 0 }
$workspace=Split-Path $PSScriptRoot -Parent
$values=@{}
Get-Content -LiteralPath (Join-Path $workspace '.env') | ForEach-Object { if ($_ -match '^([A-Za-z_][A-Za-z0-9_]*)=(.*)$') { $values[$Matches[1]]=$Matches[2].Trim().Trim('"').Trim("'") } }
if (-not $ApiUrl) { $ApiUrl=(Get-Content -LiteralPath (Join-Path $workspace 'deploy/api-url.txt') -Raw).Trim() }
if ($ApiUrl -notmatch '^https://[a-zA-Z0-9.-]+\.run\.app$') { throw 'Verified HTTPS Cloud Run URL required.' }
$values['LEADENGINE_API_URL']=$ApiUrl;$values['APP_ENV']='production'
Set-Location -LiteralPath (Join-Path $workspace 'dashboard')
& vercel link --yes --project=$ProjectName --scope=$Scope
if ($LASTEXITCODE -ne 0) { throw 'Vercel linking failed.' }
& (Join-Path $workspace '.venv/Scripts/python.exe') (Join-Path $workspace 'scripts/configure_vercel_env.py') --api-url $ApiUrl
if ($LASTEXITCODE -ne 0) { throw 'Vercel server environment configuration failed.' }
& vercel deploy --prod --yes --scope=$Scope
if ($LASTEXITCODE -ne 0) { throw 'Vercel deployment failed.' }
