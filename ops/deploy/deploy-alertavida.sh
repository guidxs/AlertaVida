#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

# Prerequisites on Amazon Linux 2023: bash, curl, git, python3, util-linux
# (flock), Docker Engine, and the Docker Compose v2 plugin. Install/configure
# these separately; this script intentionally does not install host packages.

readonly APP_DIR="/home/ec2-user/AlertaVida"
readonly COMPOSE_FILE="$APP_DIR/compose.yaml"
readonly ENV_FILE="/etc/alertavida/alertavida.env"
readonly ENV_LINK="$APP_DIR/mvp/.env"
readonly STATE_DIR="/var/lib/alertavida-deploy"
readonly DEPLOYED_STATE_FILE="$STATE_DIR/deployed.state"
readonly LEGACY_DEPLOYED_SHA_FILE="$STATE_DIR/deployed.sha"
readonly LOCK_FILE="$STATE_DIR/deploy.lock"
readonly API_URL="https://api.github.com/repos/guidxs/AlertaVida/actions/workflows/deploy-blindado.yml/runs?branch=main&event=push&per_page=1"
readonly EXPECTED_REPOSITORY="guidxs/AlertaVida"
readonly EXPECTED_WORKFLOW="Deploy Blindado"
readonly PROJECT_NAME="alertavida"
readonly BACKEND_IMAGE="alertavida-backend:latest"
readonly FRONTEND_IMAGE="alertavida-frontend:latest"
readonly BACKEND_ROLLBACK_IMAGE="alertavida-backend:rollback"
readonly FRONTEND_ROLLBACK_IMAGE="alertavida-frontend:rollback"

ENV_LINK_CREATED=0
TRANSACTION_ACTIVE=0
CHECKOUT_ATTEMPTED=0
BACKEND_BACKUP_PRESENT=0
FRONTEND_BACKUP_PRESENT=0
DEPLOYED_STATE_EXISTS=0
ROLLBACK_SHA=""
APPROVED_SHA=""
ROLLBACK_BACKEND_IMAGE_ID=""
ROLLBACK_FRONTEND_IMAGE_ID=""

log() {
    local level="$1"
    shift
    printf '%s [%s] %s\n' "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" "$level" "$*"
}

die() {
    log ERROR "$1"
    exit 1
}

on_error() {
    local status=$?
    local line="$1"
    trap - ERR
    log ERROR "Unexpected failure at script line ${line} (exit ${status})."
    exit "$status"
}

service_health_check() {
    local container_id
    local health
    local attempt

    for ((attempt = 1; attempt <= 36; attempt++)); do
        container_id="$(WEB_PORT=80 docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" ps -q backend 2>/dev/null || true)"
        if [[ -n "$container_id" ]]; then
            health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}missing{{end}}' "$container_id" 2>/dev/null || true)"
            case "$health" in
                healthy)
                    log INFO "Backend healthcheck is healthy."
                    return 0
                    ;;
                unhealthy)
                    log ERROR "Backend healthcheck reported unhealthy."
                    return 1
                    ;;
            esac
        fi
        sleep 5
    done

    log ERROR "Backend did not become healthy within 180 seconds."
    return 1
}

active_container_image_id() {
    local service="$1"
    local container_id
    local image_id

    container_id="$(WEB_PORT=80 docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" ps -q "$service" 2>/dev/null || true)"
    [[ "$container_id" =~ ^[[:xdigit:]]{64}$ ]] || return 1
    image_id="$(docker inspect --format '{{.Image}}' "$container_id" 2>/dev/null || true)"
    [[ "$image_id" =~ ^sha256:[[:xdigit:]]{64}$ ]] || return 1
    docker image inspect "$image_id" >/dev/null 2>&1 || return 1
    printf '%s\n' "$image_id"
}

check_build_space() {
    local available_kib

    available_kib="$(df -Pk -- "$APP_DIR" | awk 'END {print $4}')" || die "Could not check free space for the project filesystem."
    [[ "$available_kib" =~ ^[0-9]+$ ]] || die "Could not parse free space for the project filesystem."
    ((available_kib >= 1536 * 1024)) || die "Less than 1.5 GiB is available on the project filesystem; refusing to build."
    log INFO "Project filesystem has at least 1.5 GiB available for the build."
}

http_check() {
    local path="$1"
    local attempt
    local http_status

    for ((attempt = 1; attempt <= 36; attempt++)); do
        http_status="$(curl --silent --output /dev/null --write-out '%{http_code}' --max-time 10 "http://127.0.0.1${path}" 2>/dev/null || true)"
        if [[ "$http_status" == "200" ]]; then
            log INFO "HTTP 200 verified for ${path}."
            return 0
        fi
        sleep 5
    done

    log ERROR "HTTP check failed for ${path} after 180 seconds."
    return 1
}

verify_services() {
    service_health_check && http_check / && http_check /api/live
}

capture_image() {
    local service="$1"
    local image="$2"
    local backup_image="$3"
    local image_id=""

    image_id="$(active_container_image_id "$service")" || die "Could not identify the active ${service} container image for rollback."
    if [[ "$service" == "backend" && -n "$ROLLBACK_BACKEND_IMAGE_ID" && "$image_id" != "$ROLLBACK_BACKEND_IMAGE_ID" ]]; then
        die "Active backend image does not match the validated rollback state."
    fi
    if [[ "$service" == "frontend" && -n "$ROLLBACK_FRONTEND_IMAGE_ID" && "$image_id" != "$ROLLBACK_FRONTEND_IMAGE_ID" ]]; then
        die "Active frontend image does not match the validated rollback state."
    fi

    docker image tag "$image_id" "$backup_image"
    case "$service" in
        backend) BACKEND_BACKUP_PRESENT=1 ;;
        frontend) FRONTEND_BACKUP_PRESENT=1 ;;
    esac
    log INFO "Preserved the current ${service} image for rollback."
}

rollback() {
    local rollback_ok=1
    local checkout_ok=1
    local images_restored=1

    log WARN "Deployment failed; attempting rollback."

    if ((CHECKOUT_ATTEMPTED)) && [[ -n "$ROLLBACK_SHA" ]]; then
        if git -C "$APP_DIR" checkout --detach "$ROLLBACK_SHA"; then
            log INFO "Restored checkout to ${ROLLBACK_SHA}."
        else
            log ERROR "Could not restore the previous checkout SHA."
            checkout_ok=0
            rollback_ok=0
        fi
    fi

    if ((BACKEND_BACKUP_PRESENT)); then
        if docker image tag "$BACKEND_ROLLBACK_IMAGE" "$BACKEND_IMAGE"; then
            log INFO "Restored the previous backend image tag."
        else
            log ERROR "Could not restore the previous backend image tag."
            rollback_ok=0
        fi
    else
        log WARN "No previous backend image was available for rollback."
        rollback_ok=0
        images_restored=0
    fi

    if ((FRONTEND_BACKUP_PRESENT)); then
        if docker image tag "$FRONTEND_ROLLBACK_IMAGE" "$FRONTEND_IMAGE"; then
            log INFO "Restored the previous frontend image tag."
        else
            log ERROR "Could not restore the previous frontend image tag."
            rollback_ok=0
        fi
    else
        log WARN "No previous frontend image was available for rollback."
        rollback_ok=0
        images_restored=0
    fi

    if ((checkout_ok && images_restored)); then
        if WEB_PORT=80 docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d --no-build; then
            log INFO "Rollback Compose up command completed."
        else
            log ERROR "Rollback Compose up command failed."
            rollback_ok=0
        fi
        if verify_services; then
            log INFO "Services passed health checks after rollback attempt."
        else
            log ERROR "Services did not pass health checks after rollback attempt."
            rollback_ok=0
        fi
    else
        log ERROR "Skipped rollback Compose up because a complete previous checkout/image set is unavailable."
    fi

    log INFO "The deployment state remains unchanged because it is committed only after health checks pass."

    if ((rollback_ok)); then
        log INFO "Rollback completed successfully."
        return 0
    fi

    log ERROR "Rollback was attempted but could not be fully verified."
    return 1
}

cleanup() {
    local status=$?
    local resolved_target=""
    trap - EXIT ERR

    if ((status != 0 && TRANSACTION_ACTIVE)); then
        if rollback; then
            log INFO "Failure recovery completed; original deploy remains failed."
        else
            log ERROR "Failure recovery was incomplete; inspect systemd journal."
        fi
    fi

    if ((ENV_LINK_CREATED)) && [[ -L "$ENV_LINK" ]]; then
        resolved_target="$(readlink -f -- "$ENV_LINK" 2>/dev/null || true)"
        if [[ "$resolved_target" == "$(readlink -f -- "$ENV_FILE" 2>/dev/null || true)" ]]; then
            if rm -f -- "$ENV_LINK"; then
                log INFO "Removed the temporary Compose environment link."
            else
                log ERROR "Could not remove the temporary Compose environment link."
                if ((status == 0)); then
                    status=1
                fi
            fi
        fi
    fi

    exit "$status"
}

trap 'on_error "$LINENO"' ERR
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

for required_command in curl git python3 flock docker date sleep mktemp readlink df awk; do
    command -v "$required_command" >/dev/null 2>&1 || die "Required command is unavailable: ${required_command}."
done

docker compose version >/dev/null 2>&1 || die "Docker Compose v2 is required."
[[ "$(id -un)" == "ec2-user" ]] || die "This script must run as ec2-user."
[[ -d "$APP_DIR/.git" ]] || die "The expected Git checkout is missing."
[[ -f "$COMPOSE_FILE" ]] || die "The Compose file is missing."
[[ -d "$STATE_DIR" && -w "$STATE_DIR" ]] || die "StateDirectory is missing or not writable."
[[ -f "$ENV_FILE" && -r "$ENV_FILE" ]] || die "The protected application environment file is missing or unreadable."
command -v stat >/dev/null 2>&1 || die "Required command is unavailable: stat."
env_owner="$(stat -c '%U' "$ENV_FILE")" || die "Could not inspect application environment file ownership."
env_mode="$(stat -c '%a' "$ENV_FILE")" || die "Could not inspect application environment file permissions."
[[ "$env_owner" == "ec2-user" ]] || die "The application environment file must be owned by ec2-user."
[[ "$env_mode" =~ ^[0-7]{3,4}$ ]] || die "The application environment file permissions are invalid."
env_mode_value=$((8#$env_mode))
(( (env_mode_value & 077) == 0 )) || die "The application environment file must not grant group or other permissions."

exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    log INFO "Another deployment check is running; this invocation will exit."
    exit 0
fi

if [[ -e "$ENV_LINK" && ! -L "$ENV_LINK" ]]; then
    die "Refusing to overwrite a regular file at mvp/.env."
fi

if [[ -L "$ENV_LINK" ]]; then
    local_env_target="$(readlink -f -- "$ENV_LINK" 2>/dev/null || true)"
    expected_env_target="$(readlink -f -- "$ENV_FILE")"
    [[ "$local_env_target" == "$expected_env_target" ]] || die "Refusing to replace an unrelated symlink at mvp/.env."
    rm -f -- "$ENV_LINK"
fi

ln -s -- "$ENV_FILE" "$ENV_LINK"
ENV_LINK_CREATED=1

origin_url="$(git -C "$APP_DIR" remote get-url origin)"
case "$origin_url" in
    "https://github.com/${EXPECTED_REPOSITORY}.git"|"https://github.com/${EXPECTED_REPOSITORY}") ;;
    *) die "The checkout origin is not the expected public repository." ;;
esac

git -C "$APP_DIR" diff --quiet || die "Tracked working tree changes exist; refusing to overwrite them."
git -C "$APP_DIR" diff --cached --quiet || die "Staged working tree changes exist; refusing to overwrite them."
[[ -z "$(git -C "$APP_DIR" ls-files --others --exclude-standard -- mvp/frontend/package.json mvp/frontend/package-lock.json mvp/frontend/index.html mvp/frontend/vite.config.js mvp/frontend/nginx.conf mvp/frontend/src)" ]] || die "Untracked frontend build inputs exist; refusing to include them in a build."
if ! git -C "$APP_DIR" ls-files --others --ignored --exclude-standard -z -- mvp/frontend/src \
    | python3 -c '
import sys

paths = [p for p in sys.stdin.buffer.read().split(b"\0") if p]
included = []
for raw in paths:
    parts = raw.replace(b"\\", b"/").split(b"/")
    if b"node_modules" in parts or b"dist" in parts:
        continue
    included.append(raw)
raise SystemExit(1 if included else 0)
'; then
    die "Ignored or untracked frontend source files exist outside node_modules/dist; refusing to build."
fi

api_response="$(curl --silent --show-error --fail --connect-timeout 10 --max-time 30 \
    -H 'Accept: application/vnd.github+json' \
    -H 'X-GitHub-Api-Version: 2022-11-28' \
    "$API_URL")" || die "Could not query the public GitHub Actions API; no deployment will occur."

if ! APPROVED_SHA="$(python3 -c '
import json
import re
import sys

def reject():
    print("Latest workflow run response failed validation.", file=sys.stderr)
    raise SystemExit(1)

try:
    payload = json.load(sys.stdin)
except Exception:
    reject()

runs = payload.get("workflow_runs") if isinstance(payload, dict) else None
if not isinstance(runs, list) or not runs:
    reject()

run = runs[0]
if not isinstance(run, dict):
    reject()

repository = run.get("repository")
head_repository = run.get("head_repository")
if not isinstance(repository, dict) or repository.get("full_name") != "guidxs/AlertaVida":
    reject()
if not isinstance(head_repository, dict) or head_repository.get("full_name") != "guidxs/AlertaVida":
    reject()
if run.get("name") != "Deploy Blindado":
    reject()
if not str(run.get("path", "")).startswith(".github/workflows/deploy-blindado.yml@"):
    reject()
if run.get("head_branch") != "main" or run.get("event") != "push":
    reject()
if run.get("status") != "completed" or run.get("conclusion") != "success":
    reject()

sha = run.get("head_sha")
if not isinstance(sha, str) or re.fullmatch(r"[0-9a-fA-F]{40}", sha) is None:
    reject()
if not isinstance(run.get("run_number"), int) or run["run_number"] < 1:
    reject()
if not isinstance(run.get("run_attempt"), int) or run["run_attempt"] < 1:
    reject()

print(sha.lower())
' <<<"$api_response")"; then
    die "The latest main push run is pending, unsuccessful, or invalid; no earlier run will be deployed."
fi

log INFO "Latest successful main push candidate: ${APPROVED_SHA:0:12}."

git -C "$APP_DIR" fetch --no-tags origin +refs/heads/main:refs/remotes/origin/main || die "Could not fetch origin/main."
remote_main_sha="$(git -C "$APP_DIR" rev-parse 'refs/remotes/origin/main^{commit}')" || die "Could not resolve origin/main."
[[ "$remote_main_sha" == "$APPROVED_SHA" ]] || die "Approved workflow SHA does not exactly match origin/main; no deployment will occur."
git -C "$APP_DIR" cat-file -e "${APPROVED_SHA}^{commit}" || die "Approved commit is unavailable in the checkout."

if [[ -e "$DEPLOYED_STATE_FILE" || -L "$DEPLOYED_STATE_FILE" ]]; then
    DEPLOYED_STATE_EXISTS=1
    [[ -f "$DEPLOYED_STATE_FILE" && ! -L "$DEPLOYED_STATE_FILE" ]] || die "Deployment state is not a regular file."
    state_owner="$(stat -c '%U' "$DEPLOYED_STATE_FILE")" || die "Could not inspect deployment state ownership."
    state_mode="$(stat -c '%a' "$DEPLOYED_STATE_FILE")" || die "Could not inspect deployment state permissions."
    [[ "$state_owner" == "ec2-user" && "$state_mode" == "600" ]] || die "Deployment state must be owned by ec2-user with mode 600."
    mapfile -t state_lines < "$DEPLOYED_STATE_FILE" || die "Could not read deployment state."
    ((${#state_lines[@]} == 4)) || die "Deployment state is incomplete or has an unsupported format."
    [[ "${state_lines[0]}" == "format=alertavida-deploy-state-v1" ]] || die "Deployment state format is invalid."
    [[ "${state_lines[1]}" =~ ^sha=([0-9a-fA-F]{40})$ ]] || die "Deployment state SHA is invalid."
    ROLLBACK_SHA="${BASH_REMATCH[1],,}"
    [[ "${state_lines[2]}" =~ ^backend_image_id=(sha256:[0-9a-fA-F]{64})$ ]] || die "Deployment state backend image ID is invalid."
    ROLLBACK_BACKEND_IMAGE_ID="${BASH_REMATCH[1],,}"
    [[ "${state_lines[3]}" =~ ^frontend_image_id=(sha256:[0-9a-fA-F]{64})$ ]] || die "Deployment state frontend image ID is invalid."
    ROLLBACK_FRONTEND_IMAGE_ID="${BASH_REMATCH[1],,}"
    head_sha="$(git -C "$APP_DIR" rev-parse HEAD^{commit})" || die "Could not resolve the current checkout SHA."
    [[ "${head_sha,,}" == "$ROLLBACK_SHA" ]] || die "Current checkout does not match the recorded deployed SHA."
    git -C "$APP_DIR" cat-file -e "${ROLLBACK_SHA}^{commit}" || die "Stored deployment SHA is unavailable for rollback."
    active_backend_image_id="$(active_container_image_id backend)" || die "Could not identify the active backend image."
    active_frontend_image_id="$(active_container_image_id frontend)" || die "Could not identify the active frontend image."
    [[ "$active_backend_image_id" == "$ROLLBACK_BACKEND_IMAGE_ID" ]] || die "Active backend image does not match deployment state."
    [[ "$active_frontend_image_id" == "$ROLLBACK_FRONTEND_IMAGE_ID" ]] || die "Active frontend image does not match deployment state."
else
    [[ ! -e "$LEGACY_DEPLOYED_SHA_FILE" && ! -L "$LEGACY_DEPLOYED_SHA_FILE" ]] || die "Legacy or incomplete deployment state exists; refusing bootstrap."
    ROLLBACK_SHA="$(git -C "$APP_DIR" rev-parse HEAD^{commit})" || die "Could not resolve the current checkout SHA for bootstrap."
    ROLLBACK_BACKEND_IMAGE_ID="$(active_container_image_id backend)" || die "Bootstrap requires an identifiable active backend container image."
    ROLLBACK_FRONTEND_IMAGE_ID="$(active_container_image_id frontend)" || die "Bootstrap requires an identifiable active frontend container image."
fi

if ((DEPLOYED_STATE_EXISTS)) && [[ "$ROLLBACK_SHA" == "$APPROVED_SHA" ]]; then
    log INFO "Approved SHA is already deployed; nothing to do."
    exit 0
fi

capture_image backend "$BACKEND_IMAGE" "$BACKEND_ROLLBACK_IMAGE"
capture_image frontend "$FRONTEND_IMAGE" "$FRONTEND_ROLLBACK_IMAGE"

TRANSACTION_ACTIVE=1
CHECKOUT_ATTEMPTED=1
git -C "$APP_DIR" checkout --detach "$APPROVED_SHA" || die "Could not checkout the approved SHA."
log INFO "Checked out approved SHA ${APPROVED_SHA:0:12}."

check_build_space
WEB_PORT=80 docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" build backend || die "Backend image build failed."
check_build_space
WEB_PORT=80 docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" build frontend || die "Frontend image build failed."

git -C "$APP_DIR" fetch --no-tags origin +refs/heads/main:refs/remotes/origin/main || die "Could not recheck origin/main before activation."
remote_main_sha="$(git -C "$APP_DIR" rev-parse 'refs/remotes/origin/main^{commit}')" || die "Could not resolve the refreshed origin/main."
[[ "$remote_main_sha" == "$APPROVED_SHA" ]] || die "origin/main advanced during the build; refusing to activate this SHA."

git -C "$APP_DIR" fetch --no-tags origin +refs/heads/main:refs/remotes/origin/main || die "Could not perform the final origin/main check before activation."
remote_main_sha="$(git -C "$APP_DIR" rev-parse 'refs/remotes/origin/main^{commit}')" || die "Could not resolve the final origin/main SHA."
[[ "$remote_main_sha" == "$APPROVED_SHA" ]] || die "origin/main changed before activation; refusing to activate this SHA."

WEB_PORT=80 docker compose -p "$PROJECT_NAME" -f "$COMPOSE_FILE" up -d --no-build || die "Compose update failed."
verify_services || die "Post-deploy health checks failed."

deployed_backend_image_id="$(active_container_image_id backend)" || die "Could not identify the healthy backend image for deployment state."
deployed_frontend_image_id="$(active_container_image_id frontend)" || die "Could not identify the healthy frontend image for deployment state."
state_temporary_file="$(mktemp "$STATE_DIR/.deployed.state.XXXXXX")" || die "Could not create temporary deployment state."
if ! printf 'format=alertavida-deploy-state-v1\nsha=%s\nbackend_image_id=%s\nfrontend_image_id=%s\n' \
    "$APPROVED_SHA" "$deployed_backend_image_id" "$deployed_frontend_image_id" > "$state_temporary_file"; then
    rm -f -- "$state_temporary_file"
    die "Could not write temporary deployment state."
fi
chmod 600 "$state_temporary_file" || die "Could not secure temporary deployment state."
mv -f -- "$state_temporary_file" "$DEPLOYED_STATE_FILE" || die "Could not save deployed state."
TRANSACTION_ACTIVE=0

log INFO "Deployment completed successfully at ${APPROVED_SHA:0:12}."
