# Deployment Guide

This guide describes how to deploy the Travel Engine to Google Cloud Platform.

## Prerequisites
1. `gcloud` CLI installed and authenticated.
2. Firebase CLI installed (`npm install -g firebase-tools`).
3. A GCP Project with billing enabled.

## 1. Provision Infrastructure
Run the provisioning script to enable APIs, create a Service Account, Artifact Registry repository, and Cloud SQL instance.

```bash
cd infra/gcp
export PROJECT_ID="your-gcp-project-id"
export REGION="us-central1"
./provision-gcp.sh
```

## 2. Deploy Services
Once infrastructure is provisioned, you can deploy both backend and frontend.

```bash
export PROJECT_ID="your-gcp-project-id"
export REGION="us-central1"
./deploy.sh
```

## IAM & Least Privilege
The Service Account `travel-engine-sa` is assigned the following roles:
- `roles/cloudsql.client`: To connect to PostgreSQL.
- `roles/secretmanager.secretAccessor`: To read database credentials.
- `roles/datastore.user`: To sync Firestore realtime state.
- `roles/aiplatform.user`: To invoke Vertex AI Gemini.
- `roles/pubsub.publisher` / `roles/cloudtasks.enqueuer`: To queue background replanning tasks.

The frontend does not require backend credentials. It passes a Firebase Auth JWT to the backend, which is validated by the Admin SDK.
