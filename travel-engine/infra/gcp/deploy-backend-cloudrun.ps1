<#
.SYNOPSIS
  Backend only: Cloud Build Docker image -> Artifact Registry -> Cloud Run (travel-engine-backend).

.PARAMETER ProjectId
  GCP project id. Or set $env:PROJECT_ID .

.PARAMETER Region
  Must match Artifact Registry and Cloud SQL region.

.PARAMETER AppName
  Service name = {AppName}-backend, repo = {AppName}-repo, instance = {AppName}-db-instance.

.PARAMETER CorsOrigins
  Value for CORS_ORIGINS env (e.g. * or https://your-frontend.run.app).

.PARAMETER NoCpuBoost
  Pass if gcloud rejects --cpu-boost.

.PARAMETER NoCloudSql
  Omit --add-cloudsql-instances (only if DATABASE_URL does not use Cloud SQL socket).

.PREREQUISITES
  - Secrets gemini-api-key and database-url exist; SA {AppName}-sa has secretAccessor + cloudsql.client
  - Artifact Registry {AppName}-repo exists
#>

param (
  [string]$ProjectId = $env:PROJECT_ID,
  [string]$Region = "us-central1",
  [string]$AppName = "travel-engine",
  [string]$CorsOrigins = "*",
  [switch]$NoCpuBoost,
  [switch]$NoCloudSql
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($PSVersionTable.PSVersion.Major -ge 7) {
  try { $PSNativeCommandUseErrorActionPreference = $false } catch {}
}

if (-not $ProjectId) {
  throw "Set -ProjectId or `$env:PROJECT_ID ."
}

$TravelEngineRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$BackendDir = Join-Path $TravelEngineRoot "backend"
if (-not (Test-Path -LiteralPath $BackendDir)) {
  throw "Backend not found: $BackendDir - run from travel-engine/infra/gcp/"
}

$ImageTag = "latest"
$CloudRunService = "${AppName}-backend"
$ArtifactRepo = "${AppName}-repo"
$SqlInstanceId = "${AppName}-db-instance"
$CloudSqlConnName = "${ProjectId}:${Region}:${SqlInstanceId}"
$ImageUrl = "${Region}-docker.pkg.dev/${ProjectId}/${ArtifactRepo}/backend:${ImageTag}"
$RunServiceAccount = "${AppName}-sa@${ProjectId}.iam.gserviceaccount.com"

Write-Host "--- gcloud project $ProjectId ---"
gcloud config set project $ProjectId

Write-Host "--- Cloud Build: $ImageUrl ---"
Push-Location $BackendDir
try {
  gcloud builds submit --tag $ImageUrl --project $ProjectId
  if ($LASTEXITCODE -ne 0) { throw "gcloud builds submit failed: $LASTEXITCODE" }
}
finally {
  Pop-Location
}

Write-Host "--- Cloud Run deploy: $CloudRunService ---"
$deployArgs = @(
  "run", "deploy", $CloudRunService,
  "--project", $ProjectId,
  "--region", $Region,
  "--image", $ImageUrl,
  "--platform", "managed",
  "--service-account", $RunServiceAccount,
  "--allow-unauthenticated",
  "--set-secrets", "GEMINI_API_KEY=gemini-api-key:latest,DATABASE_URL=database-url:latest",
  "--update-env-vars", "PROJECT_ID=${ProjectId},REGION=${Region},CORS_ORIGINS=${CorsOrigins}"
)

if (-not $NoCpuBoost) {
  $deployArgs += "--cpu-boost"
}

if (-not $NoCloudSql) {
  $deployArgs += "--add-cloudsql-instances"
  $deployArgs += $CloudSqlConnName
}

& gcloud @deployArgs

if ($LASTEXITCODE -ne 0) {
  throw "gcloud run deploy failed: $LASTEXITCODE"
}

$url = gcloud run services describe $CloudRunService --region $Region --project $ProjectId --format "value(status.url)"
Write-Host ""
Write-Host "Backend URL: $url"
Write-Host "API base for frontend: $($url)/api/v1"
Write-Host "Done."
