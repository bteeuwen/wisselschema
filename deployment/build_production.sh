#!/bin/bash
# ============================================================================
# Production Docker Build and Deploy Script
#
# Usage:
#   ./deployment/build_production.sh [IMAGE_TAG] [--deploy]
#
# Examples:
#   ./deployment/build_production.sh              # Build and push as :latest
#   ./deployment/build_production.sh v1.0.0       # Build and push as :v1.0.0
#   ./deployment/build_production.sh latest --deploy  # Build, push, and deploy
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SECRETS_FILE="$SCRIPT_DIR/github_secrets.env"
TFDIR="$SCRIPT_DIR/scaleway"

IMAGE_TAG="${1:-latest}"
DEPLOY=false
if [ "$2" = "--deploy" ] || [ "$1" = "--deploy" ]; then
    DEPLOY=true
    if [ "$1" = "--deploy" ]; then
        IMAGE_TAG="latest"
    fi
fi

if [ -f "$SECRETS_FILE" ]; then
    echo "Loading credentials..."
    set -a
    source "$SECRETS_FILE"
    set +a
fi

terraform_output() {
    local name=$1
    if ! command -v terraform &>/dev/null || [ ! -d "$TFDIR" ]; then return; fi
    terraform -chdir="$TFDIR" output -raw "$name" 2>/dev/null || true
}

normalize_container_id() {
    local value=${1:-}
    value="${value##*/}"
    if [ "$value" = "null" ] || [[ ! "$value" =~ ^[0-9a-fA-F-]{36}$ ]]; then
        value=""
    fi
    printf '%s' "$value"
}

if [ -z "${SCW_REGISTRY_ENDPOINT:-}" ]; then
    SCW_REGISTRY_ENDPOINT="$(terraform_output registry_endpoint)"
fi

SCW_CONTAINER_ID="$(normalize_container_id "${SCW_CONTAINER_ID:-}")"
if [ -z "$SCW_CONTAINER_ID" ]; then
    SCW_CONTAINER_ID="$(normalize_container_id "$(terraform_output container_id)")"
fi

if [ -z "$SCW_REGISTRY_ENDPOINT" ]; then
    echo "Error: SCW_REGISTRY_ENDPOINT is not set"
    echo "  Set it in $SECRETS_FILE or apply Terraform first."
    exit 1
fi

if ! command -v scw &>/dev/null; then
    echo "Error: Scaleway CLI (scw) is not installed"
    exit 1
fi

if [ "$DEPLOY" = true ] && ! command -v jq &>/dev/null; then
    echo "Error: jq is required for deployment status checks"
    exit 1
fi

LOCAL_IMAGE="wisselschema-app:${IMAGE_TAG}"
REMOTE_IMAGE="${SCW_REGISTRY_ENDPOINT}/wisselschema-app:${IMAGE_TAG}"

echo ""
echo "Building Docker image..."
echo "  Local tag:  $LOCAL_IMAGE"
echo "  Remote tag: $REMOTE_IMAGE"
echo ""

cd "$PROJECT_ROOT"

docker build \
    -t "$LOCAL_IMAGE" \
    -t "$REMOTE_IMAGE" \
    -f Dockerfile \
    .

echo ""
echo "Build complete!"
echo ""

echo "Logging in to Scaleway Container Registry..."
scw registry login

echo ""
echo "Pushing image to registry..."
docker push "$REMOTE_IMAGE"

if [ "$IMAGE_TAG" != "latest" ]; then
    REMOTE_LATEST="${SCW_REGISTRY_ENDPOINT}/wisselschema-app:latest"
    echo "Tagging and pushing as :latest..."
    docker tag "$REMOTE_IMAGE" "$REMOTE_LATEST"
    docker push "$REMOTE_LATEST"
fi

echo ""
echo "Image pushed: $REMOTE_IMAGE"

if [ "$DEPLOY" = true ]; then
    echo ""
    echo "Deploying to Scaleway..."

    if [ -z "$SCW_CONTAINER_ID" ]; then
        if ! command -v terraform &>/dev/null; then
            echo "Error: terraform is required to bootstrap the first container deployment"
            exit 1
        fi

        echo "Bootstrapping serverless container via Terraform..."
        terraform -chdir="$TFDIR" apply -auto-approve -var="create_app_container=true"

        SCW_CONTAINER_ID="$(normalize_container_id "$(terraform_output container_id)")"
        if [ -z "$SCW_CONTAINER_ID" ]; then
            echo "Error: failed to obtain container ID from Terraform output"
            exit 1
        fi

        echo "  Created container: $SCW_CONTAINER_ID"
    fi

    scw container container update "$SCW_CONTAINER_ID" \
        image="$REMOTE_IMAGE" \
        region=fr-par

    echo "Waiting for update to settle..."
    for i in $(seq 1 24); do
        STATUS=$(scw container container get "$SCW_CONTAINER_ID" -o json region=fr-par | jq -r '.status')
        if [ "$STATUS" = "ready" ] || [ "$STATUS" = "created" ] || [ "$STATUS" = "error" ]; then
            break
        fi
        sleep 10
    done

    scw container container redeploy "$SCW_CONTAINER_ID" region=fr-par

    echo "Waiting for deployment..."
    for i in $(seq 1 12); do
        STATUS=$(scw container container get "$SCW_CONTAINER_ID" -o json region=fr-par | jq -r '.status')
        if [ "$STATUS" = "ready" ] || [ "$STATUS" = "created" ]; then
            break
        fi
        sleep 10
    done

    ENDPOINT=$(scw container container get "$SCW_CONTAINER_ID" -o json region=fr-par | jq -r '.domain_name')

    echo ""
    echo "Deployment complete!"
    echo "  Status: $STATUS"
    echo "  URL: https://$ENDPOINT"
else
    echo ""
    echo "To deploy, run:"
    echo "  ./deployment/build_production.sh $IMAGE_TAG --deploy"
fi
