#!/usr/bin/env bash

set -euo pipefail

# ScreenPilot backend deploy helper for chunk 7.
# Usage:
#   GEMINI_API_KEY=... ./backend/scripts/deploy_cloud_run.sh

PROJECT_ID="${PROJECT_ID:-gen-lang-client-0188455373}"
REGION="${REGION:-asia-south1}"
SERVICE_NAME="${SERVICE_NAME:-screenpilot-backend}"
REPOSITORY="${REPOSITORY:-screenpilot}"
TAG="${TAG:-$(date +%Y%m%d-%H%M%S)}"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_EMAIL:-screenpilot-runtime@${PROJECT_ID}.iam.gserviceaccount.com}"
BUILD_MODE="${BUILD_MODE:-auto}" # auto | docker | cloudbuild

PERSISTENCE_BACKEND="${PERSISTENCE_BACKEND:-gcp}"
GCS_BUCKET_NAME="${GCS_BUCKET_NAME:-screenpilot-shots}"
GCS_SIGNED_URL_TTL_SECONDS="${GCS_SIGNED_URL_TTL_SECONDS:-900}"
RUNS_COLLECTION="${RUNS_COLLECTION:-runs}"
RUN_STEPS_SUBCOLLECTION="${RUN_STEPS_SUBCOLLECTION:-runSteps}"
TIMESHEET_URL="${TIMESHEET_URL:-https://timesheet-demo.netlify.app/}"

if [[ -z "${GEMINI_API_KEY:-}" ]]; then
  echo "ERROR: GEMINI_API_KEY is required."
  echo "Export it before running:"
  echo "  export GEMINI_API_KEY='...'"
  exit 1
fi

command -v gcloud >/dev/null

IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${SERVICE_NAME}:${TAG}"

build_with_docker() {
  command -v docker >/dev/null
  echo "==> Building image with local Docker: ${IMAGE_URI}"
  docker build -f backend/Dockerfile -t "${IMAGE_URI}" .
  echo "==> Pushing image"
  docker push "${IMAGE_URI}"
}

build_with_cloudbuild() {
  echo "==> Building image with Cloud Build: ${IMAGE_URI}"
  tmp_config="$(mktemp)"
  cat > "${tmp_config}" <<EOF
steps:
  - name: gcr.io/cloud-builders/docker
    args:
      - build
      - -f
      - backend/Dockerfile
      - -t
      - ${IMAGE_URI}
      - .
images:
  - ${IMAGE_URI}
EOF
  gcloud builds submit --config "${tmp_config}" .
  rm -f "${tmp_config}"
}

if [[ "${BUILD_MODE}" == "docker" ]]; then
  build_with_docker
elif [[ "${BUILD_MODE}" == "cloudbuild" ]]; then
  build_with_cloudbuild
else
  if command -v docker >/dev/null 2>&1; then
    build_with_docker
  else
    echo "==> docker not found locally, using Cloud Build"
    build_with_cloudbuild
  fi
fi

echo "==> Deploying to Cloud Run"
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE_URI}" \
  --region "${REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --service-account "${SERVICE_ACCOUNT_EMAIL}" \
  --set-env-vars "GEMINI_API_KEY=${GEMINI_API_KEY},PERSISTENCE_BACKEND=${PERSISTENCE_BACKEND},GCP_PROJECT_ID=${PROJECT_ID},GCP_REGION=${REGION},GCS_BUCKET_NAME=${GCS_BUCKET_NAME},GCS_SIGNED_URL_TTL_SECONDS=${GCS_SIGNED_URL_TTL_SECONDS},RUNS_COLLECTION=${RUNS_COLLECTION},RUN_STEPS_SUBCOLLECTION=${RUN_STEPS_SUBCOLLECTION},TIMESHEET_URL=${TIMESHEET_URL}" \
  --port 8000

SERVICE_URL="$(gcloud run services describe "${SERVICE_NAME}" --region "${REGION}" --format='value(status.url)')"
echo
echo "Deploy complete."
echo "  SERVICE_URL=${SERVICE_URL}"
echo "  IMAGE_URI=${IMAGE_URI}"
echo
echo "Quick checks:"
echo "  curl \"${SERVICE_URL}/api/health\""
echo "  open \"${SERVICE_URL}/docs\""

