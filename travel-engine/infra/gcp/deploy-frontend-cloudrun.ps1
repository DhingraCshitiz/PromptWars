<#
.SYNOPSIS
  Build the Angular app in Cloud Build, push to Artifact Registry, deploy SPA to Cloud Run (nginx).

.PARAMETER ProjectId
  GCP / Firebase project id (must match Artifact Registry and existing travel-engine-repo).

.PARAMETER Region
  Same region as Artifact Registry (e.g. us-central1).

.PARAMETER AppName
  Prefix for Cloud Run service name: {AppName}-frontend .

.PREREQUISITES
  - gcloud auth and project access
  - Artifact Registry repository {AppName}-repo (e.g. provision-gcp.ps1)
  - Angular production apiBaseUrl already set in src/environments/environment.prod.ts

.NOTES
  Service URL is printed at the end. Set CORS on the API to include this origin if needed.
#>

param (
  [string]$ProjectId = "",
  [string]$Region = "us-central1",
  [string]$AppName = "travel-engine"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($PSVersionTable.PSVersion.Major -ge 7) {
  try { $PSNativeCommandUseErrorActionPreference = $false } catch {}
}

if (-not $ProjectId) {
  $ProjectId = $env:PROJECT_ID
}
if (-not $ProjectId) {
  throw "Set -ProjectId or `$env:PROJECT_ID to your GCP project id."
}

$TravelEngineRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$FrontendDir = Join-Path $TravelEngineRoot "frontend"
if (-not (Test-Path -LiteralPath $FrontendDir)) {
  throw "Frontend not found: $FrontendDir"
}

$ArtifactRepo = "${AppName}-repo"
$ServiceName = "${AppName}-frontend"
$ImageTag = "latest"
$ImageUrl = "${Region}-docker.pkg.dev/${ProjectId}/${ArtifactRepo}/frontend:${ImageTag}"

Write-Host "--- gcloud project ---"
gcloud config set project $ProjectId

Write-Host "--- Cloud Build: frontend image -> $ImageUrl ---"
Push-Location $FrontendDir
try {
  gcloud builds submit --tag $ImageUrl --project $ProjectId
  if ($LASTEXITCODE -ne 0) { throw "gcloud builds submit failed: $LASTEXITCODE" }
}
finally {
  Pop-Location
}

Write-Host "--- Cloud Run deploy: $ServiceName ---"
gcloud run deploy $ServiceName `
  --project $ProjectId `
  --region $Region `
  --image $ImageUrl `
  --platform managed `
  --allow-unauthenticated `
  --port 8080

if ($LASTEXITCODE -ne 0) { throw "gcloud run deploy failed: $LASTEXITCODE" }

$url = gcloud run services describe $ServiceName --region $Region --project $ProjectId --format "value(status.url)"
Write-Host ""
Write-Host "Frontend (Cloud Run): $url"
Write-Host "Ensure environment.prod.ts apiBaseUrl points to your API (e.g. .../api/v1)."
Write-Host "If the API uses explicit CORS origins, add: $url"
Write-Host "Done."
