param (
    [string]$ProjectId = $env:PROJECT_ID,
    [string]$Region = "us-central1",
    [string]$AppName = "travel-engine"
)

if (-not $ProjectId) {
    Write-Error "Error: ProjectId is required. Set `$env:PROJECT_ID or pass it as a parameter."
    exit 1
}

Write-Host "Provisioning GCP resources for project $ProjectId in $Region..."

# Enable APIs
gcloud services enable `
  run.googleapis.com `
  cloudbuild.googleapis.com `
  artifactregistry.googleapis.com `
  secretmanager.googleapis.com `
  sqladmin.googleapis.com `
  firestore.googleapis.com `
  firebase.googleapis.com `
  identitytoolkit.googleapis.com `
  aiplatform.googleapis.com `
  maps-backend.googleapis.com `
  routes.googleapis.com `
  places.googleapis.com `
  pubsub.googleapis.com `
  cloudtasks.googleapis.com `
  --project $ProjectId

# Create Artifact Registry
try {
    gcloud artifacts repositories create "${AppName}-repo" `
      --repository-format=docker `
      --location=$Region `
      --project $ProjectId
} catch {
    Write-Host "Repository may already exist."
}

# Create Service Account
$SaName = "${AppName}-sa"
$SaEmail = "${SaName}@${ProjectId}.iam.gserviceaccount.com"
try {
    gcloud iam service-accounts create $SaName `
      --display-name="Service Account for $AppName" `
      --project $ProjectId
} catch {
    Write-Host "Service account may already exist."
}

# Assign Roles
$Roles = @(
  "roles/cloudsql.client",
  "roles/secretmanager.secretAccessor",
  "roles/datastore.user",
  "roles/aiplatform.user",
  "roles/pubsub.publisher",
  "roles/cloudtasks.enqueuer"
)

foreach ($Role in $Roles) {
    gcloud projects add-iam-policy-binding $ProjectId `
      --member="serviceAccount:${SaEmail}" `
      --role="$Role" > $null
}

# Create Cloud SQL
$SqlInstance = "${AppName}-db-instance"
try {
    gcloud sql instances create $SqlInstance `
      --database-version=POSTGRES_15 `
      --tier=db-f1-micro `
      --region=$Region `
      --project=$ProjectId
} catch {
    Write-Host "SQL instance may already exist."
}

try {
    gcloud sql databases create traveldb `
      --instance=$SqlInstance `
      --project=$ProjectId
} catch {
    Write-Host "Database may already exist."
}

# Create Secrets
try {
    gcloud secrets create DB_PASSWORD --replication-policy="automatic" --project=$ProjectId
} catch {
    Write-Host "Secret DB_PASSWORD exists."
}

"CHANGE_ME" | gcloud secrets versions add DB_PASSWORD --data-file=- --project=$ProjectId

# Initialize Firestore
try {
    gcloud firestore databases create --location=$Region --type=firestore-native --project=$ProjectId
} catch {
    Write-Host "Firestore exists."
}

Write-Host "Provisioning complete."
