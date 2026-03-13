#!/usr/bin/env bash

set -euo pipefail

# ScreenPilot Cloud Run setup for chunk 6 prerequisites.
# Usage:
#   PROJECT_ID=gen-lang-client-0188455373 REGION=asia-south1 ./backend/scripts/setup_docker_env.sh

PROJECT_ID="${PROJECT_ID:-gen-lang-client-0188455373}"
REGION="${REGION:-asia-south1}"
REPOSITORY="${REPOSITORY:-screenpilot}"
BUCKET_NAME="${BUCKET_NAME:-screenpilot-shots}"
SERVICE_ACCOUNT_NAME="${SERVICE_ACCOUNT_NAME:-screenpilot-runtime}"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "==> Validating local prerequisites"
command -v gcloud >/dev/null
if ! command -v docker >/dev/null 2>&1; then
  echo "WARN: docker not found locally. Deploy script can use BUILD_MODE=cloudbuild."
fi

echo "==> Configuring gcloud defaults"
gcloud config set project "${PROJECT_ID}" >/dev/null
gcloud config set run/region "${REGION}" >/dev/null
gcloud config set artifacts/location "${REGION}" >/dev/null

echo "==> Enabling required Google APIs"
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  firestore.googleapis.com \
  storage.googleapis.com \
  iam.googleapis.com \
  iamcredentials.googleapis.com >/dev/null

echo "==> Ensuring Artifact Registry repository exists"
if ! gcloud artifacts repositories describe "${REPOSITORY}" --location="${REGION}" >/dev/null 2>&1; then
  gcloud artifacts repositories create "${REPOSITORY}" \
    --repository-format=docker \
    --location="${REGION}" \
    --description="ScreenPilot backend images" >/dev/null
fi

echo "==> Ensuring screenshot bucket exists"
if ! gcloud storage buckets describe "gs://${BUCKET_NAME}" >/dev/null 2>&1; then
  gcloud storage buckets create "gs://${BUCKET_NAME}" \
    --location="${REGION}" \
    --uniform-bucket-level-access >/dev/null
fi

echo "==> Ensuring Firestore Native database exists"
if ! gcloud firestore databases describe --database='(default)' >/dev/null 2>&1; then
  gcloud firestore databases create --location="${REGION}" >/dev/null
fi

echo "==> Ensuring runtime service account exists"
if ! gcloud iam service-accounts describe "${SERVICE_ACCOUNT_EMAIL}" >/dev/null 2>&1; then
  gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
    --display-name="ScreenPilot runtime" >/dev/null
fi

echo "==> Granting runtime IAM roles"
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/datastore.user" \
  --quiet >/dev/null

gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/artifactregistry.reader" \
  --quiet >/dev/null

gcloud storage buckets add-iam-policy-binding "gs://${BUCKET_NAME}" \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/storage.objectAdmin" \
  --quiet >/dev/null

gcloud iam service-accounts add-iam-policy-binding "${SERVICE_ACCOUNT_EMAIL}" \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/iam.serviceAccountTokenCreator" \
  --quiet >/dev/null

echo "==> Configuring Docker auth for Artifact Registry"
gcloud auth configure-docker "${REGION}-docker.pkg.dev" --quiet >/dev/null

echo
echo "Setup complete."
echo "  PROJECT_ID=${PROJECT_ID}"
echo "  REGION=${REGION}"
echo "  REPOSITORY=${REPOSITORY}"
echo "  BUCKET_NAME=${BUCKET_NAME}"
echo "  SERVICE_ACCOUNT_EMAIL=${SERVICE_ACCOUNT_EMAIL}"

