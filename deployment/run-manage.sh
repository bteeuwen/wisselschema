#!/bin/bash
# ============================================================================
# Run Django management commands against the production environment.
#
# Usage:
#   ./deployment/run-manage.sh [MANAGE_COMMAND...]
#   ./deployment/run-manage.sh --bash
#
# Examples:
#   ./deployment/run-manage.sh shell
#   ./deployment/run-manage.sh migrate
#   ./deployment/run-manage.sh createsuperuser
#   ./deployment/run-manage.sh --bash
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_FILE="$SCRIPT_DIR/github_secrets.env"
TFVARS_FILE="$SCRIPT_DIR/scaleway/terraform.tfvars"
TFDIR="$SCRIPT_DIR/scaleway"

BASH_SHELL=false
MANAGE_ARGS=()
for arg in "$@"; do
    if [[ "$arg" == "--bash" ]]; then BASH_SHELL=true;
    else MANAGE_ARGS+=("$arg"); fi
done
if [[ "$BASH_SHELL" == false && ${#MANAGE_ARGS[@]} -eq 0 ]]; then
    MANAGE_ARGS=("shell")
fi

for cmd in docker scw terraform python3; do
    if ! command -v "$cmd" &>/dev/null; then
        echo "ERROR: '$cmd' is required but not found" >&2; exit 1
    fi
done

[[ -f "$SECRETS_FILE" ]] || { echo "ERROR: $SECRETS_FILE not found" >&2; exit 1; }
[[ -f "$TFVARS_FILE" ]] || { echo "ERROR: $TFVARS_FILE not found" >&2; exit 1; }

set -a; source "$SECRETS_FILE"; set +a

IMAGE="${SCW_REGISTRY_ENDPOINT}/wisselschema-app:latest"

parse_tfvars() {
    python3 - "$TFVARS_FILE" <<'PY'
import sys
path = sys.argv[1]
with open(path) as f:
    for line in f:
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line: continue
        key, _, rest = line.partition('=')
        key = key.strip()
        if not key.replace('_', '').isalnum(): continue
        value = rest.strip()
        if value.startswith('"'):
            end = value.find('"', 1)
            value = value[1:end] if end != -1 else value[1:]
        else:
            value = value.split()[0] if value.split() else ''
        print(f"TF_{key.upper()}='{value}'")
PY
}

eval "$(parse_tfvars)"

echo "Fetching MySQL host from terraform output..."
MYSQL_HOST=$(cd "$TFDIR" && terraform output -raw mysql_host 2>/dev/null) || MYSQL_HOST=""
MYSQL_HOST="${MYSQL_HOST:-}"
MYSQL_PASSWORD="${TF_MYSQL_PASSWORD:-}"
DATABASE_URL="mysql://wisselschema:${MYSQL_PASSWORD}@${MYSQL_HOST}:3306/wisselschema"

DJANGO_SECRET_KEY="${TF_DJANGO_SECRET_KEY:-}"

echo "Logging in to Scaleway Container Registry..."
scw registry login

echo "Pulling production image: $IMAGE"
docker pull "$IMAGE"

DOCKER_TTY=()
[[ -t 0 ]] && DOCKER_TTY=(-t)

DOCKER_ARGS=(
    run --rm -i "${DOCKER_TTY[@]}"
    --entrypoint ""
    -e DJANGO_DEBUG=False
    -e DJANGO_ALLOWED_HOSTS="*"
    -e "DJANGO_SECRET_KEY=${DJANGO_SECRET_KEY}"
    -e "DATABASE_URL=${DATABASE_URL}"
    "$IMAGE"
)

if [[ "$BASH_SHELL" == true ]]; then
    echo ""; echo "WARNING: Connected to the PRODUCTION database. Be careful."; echo ""
    exec docker "${DOCKER_ARGS[@]}" bash
else
    echo ""; echo "Running: python manage.py ${MANAGE_ARGS[*]}"
    [[ " ${MANAGE_ARGS[*]} " =~ " shell " || " ${MANAGE_ARGS[*]} " =~ " dbshell " ]] && \
        echo "WARNING: Connected to the PRODUCTION database. Be careful."
    echo ""
    exec docker "${DOCKER_ARGS[@]}" python manage.py "${MANAGE_ARGS[@]}"
fi
