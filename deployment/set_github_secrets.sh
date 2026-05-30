#!/bin/bash
# Push secrets to GitHub Actions. Run from the deployment/ directory.

set -e

if ! command -v gh &>/dev/null; then
    echo "Error: GitHub CLI (gh) is not installed."
    exit 1
fi

if [ ! -f "scaleway/terraform.tfvars" ]; then
    echo "Error: scaleway/terraform.tfvars not found. Run from deployment/ directory."
    exit 1
fi

if [ -f "github_secrets.env" ]; then
    echo "Loading secrets from github_secrets.env..."
    source github_secrets.env
fi

terraform_output() {
    terraform -chdir=scaleway output -raw "$1" 2>/dev/null || true
}

normalize_container_id() {
    local value=${1:-}
    value="${value##*/}"
    if [ "$value" = "null" ] || [[ ! "$value" =~ ^[0-9a-fA-F-]{36}$ ]]; then value=""; fi
    printf '%s' "$value"
}

if [ -z "${SCW_PROJECT_ID:-}" ] && command -v scw &>/dev/null; then
    SCW_PROJECT_ID=$(scw config get default-project-id 2>/dev/null || true)
fi

if [ -z "${SCW_ORGANIZATION_ID:-}" ] && command -v scw &>/dev/null; then
    SCW_ORGANIZATION_ID=$(scw config get default-organization-id 2>/dev/null || true)
fi

if [ -z "${SCW_REGISTRY_ENDPOINT:-}" ]; then
    SCW_REGISTRY_ENDPOINT=$(terraform_output registry_endpoint)
fi

SCW_CONTAINER_ID=$(normalize_container_id "${SCW_CONTAINER_ID:-}")
if [ -z "$SCW_CONTAINER_ID" ]; then
    SCW_CONTAINER_ID=$(normalize_container_id "$(terraform_output container_id)")
fi

DJANGO_SECRET_KEY=$(grep -E "^django_secret_key\s*=" scaleway/terraform.tfvars | cut -d '"' -f 2)
MYSQL_PASSWORD=$(grep -E "^mysql_password\s*=" scaleway/terraform.tfvars | cut -d '"' -f 2)

MYSQL_HOST=$(terraform_output mysql_host)
MYSQL_PORT="3306"
DATABASE_URL="mysql://wisselschema:${MYSQL_PASSWORD}@${MYSQL_HOST}:${MYSQL_PORT}/wisselschema"

set_secret() {
    local name=$1
    if [ -n "${!name}" ]; then
        echo "  Setting $name..."
        gh secret set "$name" --body "${!name}"
    else
        echo "  Warning: $name not set, skipping"
    fi
}

echo "Setting GitHub secrets..."
set_secret "DJANGO_SECRET_KEY"
set_secret "DATABASE_URL"
set_secret "SCW_ACCESS_KEY"
set_secret "SCW_SECRET_KEY"
set_secret "SCW_ORGANIZATION_ID"
set_secret "SCW_PROJECT_ID"
set_secret "SCW_REGISTRY_ENDPOINT"
set_secret "SCW_CONTAINER_ID"

echo ""
echo "GitHub secrets setup complete!"
