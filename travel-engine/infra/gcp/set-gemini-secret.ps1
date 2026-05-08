<#
.SYNOPSIS
  Create or add a new Secret Manager version for gemini-api-key and grant {AppName}-sa read access.

.PARAMETER ProjectId
  GCP project id, or set $env:PROJECT_ID.

.PARAMETER AppName
  Matches provision step: service account is {AppName}-sa@PROJECT.iam.gserviceaccount.com

.PARAMETER SkipIam
  Do not run add-iam-policy-binding (binding already exists).

.BINDING
  Cloud Run uses: --set-secrets GEMINI_API_KEY=gemini-api-key:latest
  After this script, roll the service: gcloud run services update travel-engine-backend ...

.NOTES
  ASCII-only for Windows PowerShell 5.1. Key is prompted or from $env:GEMINI_API_KEY_TO_SET (session only).
#>

param (
  [string]$ProjectId = $env:PROJECT_ID,
  [string]$AppName = "travel-engine",
  [switch]$SkipIam
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if ($PSVersionTable.PSVersion.Major -ge 7) {
  try { $PSNativeCommandUseErrorActionPreference = $false } catch {}
}

if (-not $ProjectId) {
  throw "Set -ProjectId or `$env:PROJECT_ID ."
}

function New-GcloudSecretIfMissing {
  param(
    [Parameter(Mandatory)][string] $SecretName,
    [Parameter(Mandatory)][string] $ProjectId
  )
  cmd.exe /c "gcloud secrets create $SecretName --replication-policy=automatic --project=$ProjectId 2>nul 1>nul"
}

$RunServiceAccount = "${AppName}-sa@${ProjectId}.iam.gserviceaccount.com"
$SecretName = "gemini-api-key"

$key = $env:GEMINI_API_KEY_TO_SET
if ([string]::IsNullOrWhiteSpace($key)) {
  $key = Read-Host -Prompt "Enter GEMINI_API_KEY (paste key; not saved in repo)"
}
$key = $key.Trim()
if ([string]::IsNullOrWhiteSpace($key)) {
  throw "GEMINI_API_KEY is required. Or set env GEMINI_API_KEY_TO_SET for one run only."
}

Write-Host "--- gcloud project $ProjectId ---"
gcloud config set project $ProjectId

$tmp = [IO.Path]::GetTempFileName()
try {
  $utf8 = New-Object System.Text.UTF8Encoding($false)
  [IO.File]::WriteAllText($tmp, $key, $utf8)
  $key = $null

  New-GcloudSecretIfMissing -SecretName $SecretName -ProjectId $ProjectId
  gcloud secrets versions add $SecretName --data-file=$tmp --project=$ProjectId
  if ($LASTEXITCODE -ne 0) {
    throw "gcloud secrets versions add failed: $LASTEXITCODE"
  }
}
finally {
  Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
}

if (-not $SkipIam) {
  gcloud secrets add-iam-policy-binding $SecretName `
    --project $ProjectId `
    --member "serviceAccount:$RunServiceAccount" `
    --role "roles/secretmanager.secretAccessor"
}

Write-Host ""
Write-Host "Added new version of $SecretName . Cloud Run reads GEMINI_API_KEY=gemini-api-key:latest"
Write-Host "Roll backend so instances pick it up, e.g.:"
Write-Host "  gcloud run services update ${AppName}-backend --region us-central1 --project $ProjectId"
Write-Host ""
if ($env:GEMINI_API_KEY_TO_SET) {
  Write-Host "Clear session: Remove-Item Env:GEMINI_API_KEY_TO_SET"
}
Write-Host "Done."
