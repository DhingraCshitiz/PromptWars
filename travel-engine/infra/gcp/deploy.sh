PROJECT_ID=${PROJECT_ID:-""}
REGION=${REGION:-"us-central1"}
APP_NAME=${APP_NAME:-"travel-engine"}

if [ -z "$PROJECT_ID" ]; then
  echo "Error: PROJECT_ID environment variable is required."
  exit 1
fi

echo "Building Backend..."
IMAGE_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/${APP_NAME}-repo/backend:latest"

cd ../../backend
gcloud builds submit --tag $IMAGE_URL --project $PROJECT_ID

echo "Deploying Backend to Cloud Run..."
gcloud run deploy ${APP_NAME}-backend \
  --image $IMAGE_URL \
  --platform managed \
  --region $REGION \
  --project $PROJECT_ID \
  --allow-unauthenticated \
  --set-env-vars="PROJECT_ID=$PROJECT_ID,REGION=$REGION" \
  --service-account="${APP_NAME}-sa@${PROJECT_ID}.iam.gserviceaccount.com"

echo "Building Frontend..."
cd ../frontend
# Ensure you have npm installed
npm install
npm run build

echo "Deploying Frontend to Firebase..."
# Ensure firebase CLI is logged in
firebase deploy --project $PROJECT_ID --only hosting
