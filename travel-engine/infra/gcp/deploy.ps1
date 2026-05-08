param (
    [string]$ProjectId = $env:PROJECT_ID,
    [string]$Region = "us-central1",
    [string]$AppName = "travel-engine"
)

if (-not $ProjectId) {
    Write-Error "Error: ProjectId is required. Set `$env:PROJECT_ID or pass it as a parameter."
    exit 1
}

Write-Host "Building Backend..."
$ImageUrl = "${Region}-docker.pkg.dev/${ProjectId}/${AppName}-repo/backend:latest"

Push-Location ../../backend
gcloud builds submit --tag $ImageUrl --project $ProjectId
Pop-Location

Write-Host "Deploying Backend to Cloud Run..."
gcloud run deploy "${AppName}-backend" `
  --image $ImageUrl `
  --platform managed `
  --region $Region `
  --project $ProjectId `
  --allow-unauthenticated `
  --set-env-vars="PROJECT_ID=$ProjectId,REGION=$Region" `
  --service-account="${AppName}-sa@${ProjectId}.iam.gserviceaccount.com"

Write-Host "Building Frontend..."
Push-Location ../../frontend
npm install
npm run build
Pop-Location

Write-Host "Deploying Frontend to Firebase..."
firebase deploy --project $ProjectId --only hosting
