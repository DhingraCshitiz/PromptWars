PROJECT_ID=${PROJECT_ID:-""}
REGION=${REGION:-"us-central1"}
APP_NAME=${APP_NAME:-"travel-engine"}

if [ -z "$PROJECT_ID" ]; then
  echo "Error: PROJECT_ID environment variable is required."
  exit 1
fi

echo "Provisioning GCP resources for project $PROJECT_ID in $REGION..."

# Enable APIs
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  sqladmin.googleapis.com \
  firestore.googleapis.com \
  firebase.googleapis.com \
  identitytoolkit.googleapis.com \
  aiplatform.googleapis.com \
  maps-backend.googleapis.com \
  routes.googleapis.com \
  places.googleapis.com \
  pubsub.googleapis.com \
  cloudtasks.googleapis.com \
  --project $PROJECT_ID

# Create Artifact Registry
gcloud artifacts repositories create ${APP_NAME}-repo \
  --repository-format=docker \
  --location=$REGION \
  --project $PROJECT_ID || echo "Repository may already exist."

# Create Service Account
SA_NAME="${APP_NAME}-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
gcloud iam service-accounts create $SA_NAME \
  --display-name="Service Account for $APP_NAME" \
  --project $PROJECT_ID || echo "Service account may already exist."

# Assign Roles
ROLES=(
  "roles/cloudsql.client"
  "roles/secretmanager.secretAccessor"
  "roles/datastore.user"
  "roles/aiplatform.user"
  "roles/pubsub.publisher"
  "roles/cloudtasks.enqueuer"
)
for ROLE in "${ROLES[@]}"; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="$ROLE" > /dev/null
done

# Create Cloud SQL
SQL_INSTANCE="${APP_NAME}-db-instance"
gcloud sql instances create $SQL_INSTANCE \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION \
  --project=$PROJECT_ID || echo "SQL instance may already exist."

gcloud sql databases create traveldb \
  --instance=$SQL_INSTANCE \
  --project=$PROJECT_ID || echo "Database may already exist."

# Create Secrets
gcloud secrets create DB_PASSWORD --replication-policy="automatic" --project=$PROJECT_ID || echo "Secret DB_PASSWORD exists."
echo -n "CHANGE_ME" | gcloud secrets versions add DB_PASSWORD --data-file=- --project=$PROJECT_ID

# Initialize Firestore
gcloud firestore databases create --location=$REGION --type=firestore-native --project=$PROJECT_ID || echo "Firestore exists."

echo "Provisioning complete."
