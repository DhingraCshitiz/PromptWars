<#
.SYNOPSIS
  Manual GCP deploy aligned with provision-gcp.ps1 + deploy.ps1: secrets, backend
  image (Cloud Build), Cloud Run with Cloud SQL + Gemini, then Angular build + Firebase Hosting.

.DESCRIPTION
  Prereqs: gcloud authenticated, Firebase CLI logged in, Node/npm, Firebase project
  linked to GCP, billing enabled. Run provision-gcp.ps1 once first if AR/SQL/SA are missing.

  WHERE TO FIND PLACEHOLDERS
  - YOUR_GCP_PROJECT_ID: Cloud Console project picker, or: gcloud projects list
  - Region: must match Artifact Registry + Cloud SQL (default us-central1)
  - CorsOrigins: Firebase Hosting URL (e.g. https://YOUR_ID.web.app) or custom domain
  - Cloud SQL connection name: Console > SQL > instance > Connection name
    (shape: project:region:instance-id)
  - GEMINI_API_KEY: https://aistudio.google.com/apikey (never commit; use prompt below)
  - Cloud Run URL after deploy: put in frontend/src/environments/environment.prod.ts as apiBaseUrl .../api/v1

.NOTES
  firebase.json public must match Angular output: dist/travel-engine/browser
  Save this file as UTF-8 with BOM if you use PS 5.1 and non-ASCII comments (this file stays ASCII-only).
#>

# ------------- CONFIG (edit these placeholders) -------------
$ProjectId   = "csh-promptwars"
$Region      = "us-central1"
$AppName     = "travel-engine"
$CorsOrigins = "*"

$TravelEngineRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$BackendDir       = Join-Path $TravelEngineRoot "backend"
$FrontendDir      = Join-Path $TravelEngineRoot "frontend"
$ImageTag         = "latest"
$CloudRunService  = "${AppName}-backend"
$ArtifactRepo     = "${AppName}-repo"
$SqlInstanceId    = "${AppName}-db-instance"
$CloudSqlConnName = "${ProjectId}:${Region}:${SqlInstanceId}"

$ImageUrl           = "${Region}-docker.pkg.dev/${ProjectId}/${ArtifactRepo}/backend:${ImageTag}"
$RunServiceAccount  = "${AppName}-sa@${ProjectId}.iam.gserviceaccount.com"

$SqlDbUser  = "travel_engine_user"
$SqlDbName  = "traveldb"

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# PS 7.2+: do not treat gcloud stderr (e.g. "already exists") as terminating errors.
if ($PSVersionTable.PSVersion.Major -ge 7) {
  try {
    $PSNativeCommandUseErrorActionPreference = $false
  } catch {}
}

function New-GcloudSecretIfMissing {
  param(
    [Parameter(Mandatory)][string] $SecretName,
    [Parameter(Mandatory)][string] $ProjectId
  )
  # Avoid `gcloud secrets describe` -- NOT_FOUND is written to stderr and gcloud.ps1 can stop the script.
  # Creating when the secret already exists fails harmlessly; then we always add a new version.
  cmd.exe /c "gcloud secrets create $SecretName --replication-policy=automatic --project=$ProjectId 2>nul 1>nul"
}

# ------------- 0) Sanity -------------
if ($ProjectId -eq "YOUR_GCP_PROJECT_ID") { throw "Set `$ProjectId at the top of this script." }
if (-not (Test-Path -LiteralPath $BackendDir)) {
  throw "Backend not found at $BackendDir - check script lives under travel-engine/infra/gcp."
}

Write-Host "--- gcloud project ---"
gcloud config set project $ProjectId

# ------------- 1) One-time provision (uncomment if infra not created yet) -------------
# Push-Location $PSScriptRoot
# .\provision-gcp.ps1 -ProjectId $ProjectId -Region $Region -AppName $AppName
# Pop-Location

# ------------- 2) Gemini secret -------------
$geminiPlain = Read-Host -Prompt "Enter GEMINI_API_KEY (not saved in this file)"
if ([string]::IsNullOrWhiteSpace($geminiPlain)) { throw "GEMINI_API_KEY is required." }

$tmpGemini = [IO.Path]::GetTempFileName()
try {
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  [IO.File]::WriteAllText($tmpGemini, $geminiPlain.Trim(), $utf8)
  New-GcloudSecretIfMissing -SecretName "gemini-api-key" -ProjectId $ProjectId
  gcloud secrets versions add gemini-api-key --data-file=$tmpGemini --project=$ProjectId
}
finally {
  Remove-Item -LiteralPath $tmpGemini -Force -ErrorAction SilentlyContinue
  $geminiPlain = $null
}

gcloud secrets add-iam-policy-binding gemini-api-key `
  --project $ProjectId `
  --member "serviceAccount:$RunServiceAccount" `
  --role "roles/secretmanager.secretAccessor"

# ------------- 3) DATABASE_URL secret -------------
$sqlPass = Read-Host -Prompt "PostgreSQL password for user $SqlDbUser (Cloud SQL user must already exist)" -AsSecureString
$BSTR = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sqlPass)
try {
  $sqlPassPlain = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($BSTR)
} finally {
  [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
}

if ([string]::IsNullOrWhiteSpace($sqlPassPlain)) { throw "Database password is required." }

$pwdEnc = [Uri]::EscapeDataString($sqlPassPlain)
$sqlPassPlain = $null
$dbUrlPlain = "postgresql+asyncpg://${SqlDbUser}:${pwdEnc}@/${SqlDbName}?host=/cloudsql/${CloudSqlConnName}"

$dbTmp = [IO.Path]::GetTempFileName()
try {
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  [IO.File]::WriteAllText($dbTmp, $dbUrlPlain, $utf8)
  $dbUrlPlain = $null
  New-GcloudSecretIfMissing -SecretName "database-url" -ProjectId $ProjectId
  gcloud secrets versions add database-url --data-file=$dbTmp --project=$ProjectId
}
finally {
  Remove-Item -LiteralPath $dbTmp -Force -ErrorAction SilentlyContinue
}

gcloud secrets add-iam-policy-binding database-url `
  --project $ProjectId `
  --member "serviceAccount:$RunServiceAccount" `
  --role "roles/secretmanager.secretAccessor"

Write-Host "--- If user '$SqlDbUser' does not exist, create via Console (SQL > Users) or: ---"
Write-Host "gcloud sql users create $SqlDbUser --instance=$SqlInstanceId --prompt-for-password --project=$ProjectId"

# ------------- 4) Build backend image -------------
Push-Location $BackendDir
try {
  gcloud builds submit --tag $ImageUrl --project $ProjectId
}
finally {
  Pop-Location
}

# ------------- 5) Deploy Cloud Run -------------
# --cpu-boost: extra CPU during startup (helps cold start). Remove if your gcloud is too old.
gcloud run deploy $CloudRunService `
  --project $ProjectId `
  --region $Region `
  --image $ImageUrl `
  --platform managed `
  --service-account $RunServiceAccount `
  --allow-unauthenticated `
  --cpu-boost `
  --add-cloudsql-instances $CloudSqlConnName `
  --set-secrets "GEMINI_API_KEY=gemini-api-key:latest,DATABASE_URL=database-url:latest" `
  --update-env-vars "PROJECT_ID=${ProjectId},REGION=${Region},CORS_ORIGINS=${CorsOrigins}"

if ($LASTEXITCODE -ne 0) {
  throw "Cloud Run deploy failed (`$LASTEXITCODE). Fix logs (DB, CORS, secrets) before frontend deploy. Open Cloud Logging link from message above."
}

$runUrl = gcloud run services describe $CloudRunService --region $Region --project $ProjectId --format "value(status.url)"
Write-Host ""
Write-Host "Cloud Run URL: $runUrl"
Write-Host "Set frontend apiBaseUrl to: ${runUrl}/api/v1"
Write-Host "  File: travel-engine/frontend/src/environments/environment.prod.ts"
Write-Host ""

# ------------- 6) Frontend build + Firebase Hosting -------------
Push-Location $FrontendDir
try {
  npm ci --no-audit --no-fund
  if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "npm ci failed (Windows EPERM often means esbuild.exe is locked). Close IDE tabs on node_modules,"
    Write-Host "stop ng serve/watch, then:"
    Write-Host "  Remove-Item -LiteralPath .\node_modules -Recurse -Force -ErrorAction SilentlyContinue"
    Write-Host "  npm ci --no-audit --no-fund"
    throw "npm ci failed with exit code $LASTEXITCODE"
  }

  npm run build
  if ($LASTEXITCODE -ne 0) { throw "Angular build failed with exit code $LASTEXITCODE." }

  # Firebase CLI requires a default project id (fixes: "site with no site name or target name").
  $fbRcPath = Join-Path $FrontendDir ".firebaserc"
  $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
  $fbRcBody = "{`n  `"projects`": {`n    `"default`": `"$ProjectId`"`n  }`n}` + "`n"
  [System.IO.File]::WriteAllText($fbRcPath, $fbRcBody, $utf8NoBom)

  firebase deploy --project $ProjectId --only hosting
}
finally {
  Pop-Location
}

Write-Host "Done."
