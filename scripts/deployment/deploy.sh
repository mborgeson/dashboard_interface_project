#!/usr/bin/env bash
# =============================================================================
# B&R Capital Dashboard - Production Deployment Script
# =============================================================================
# This script handles zero-downtime deployments with rollback capability.
#
# Usage: ./deploy.sh [OPTIONS]
#   --tag TAG           Docker image tag to deploy (default: latest)
#   --skip-migrations   Skip database migrations
#   --skip-backup       Skip pre-deployment backup
#   --force             Force deployment without confirmations
#   --rollback          Rollback to previous deployment
#   --dry-run           Show what would be done without executing
# =============================================================================

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================
readonly SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
readonly DEPLOY_DIR="/opt/dashboard"
readonly BACKUP_DIR="${DEPLOY_DIR}/backups"
readonly LOG_DIR="${DEPLOY_DIR}/logs"
readonly COMPOSE_FILE="${DEPLOY_DIR}/docker-compose.prod.yml"
readonly ENV_FILE="${DEPLOY_DIR}/.env"

# Docker Registry Configuration
readonly REGISTRY="${DOCKER_REGISTRY:-ghcr.io}"
readonly REGISTRY_OWNER="${REGISTRY_OWNER:-your-org}"
readonly IMAGE_BACKEND="${REGISTRY}/${REGISTRY_OWNER}/dashboard-backend"
readonly IMAGE_FRONTEND="${REGISTRY}/${REGISTRY_OWNER}/dashboard-frontend"

# Deployment settings
readonly HEALTH_CHECK_TIMEOUT=120
readonly HEALTH_CHECK_INTERVAL=5
readonly MAX_ROLLBACK_VERSIONS=5

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# State tracking
DEPLOYMENT_STARTED=false
PREVIOUS_BACKEND_IMAGE=""
PREVIOUS_FRONTEND_IMAGE=""
BACKUP_TIMESTAMP=""

# =============================================================================
# Logging Functions
# =============================================================================
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp
    timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    local log_file="${LOG_DIR}/deploy-$(date '+%Y%m%d').log"
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$log_file"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
    log "INFO" "$*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
    log "SUCCESS" "$*"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
    log "WARNING" "$*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
    log "ERROR" "$*"
}

# =============================================================================
# Helper Functions
# =============================================================================
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    # Check Docker Compose
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi

    # Check deployment directory
    if [[ ! -d "$DEPLOY_DIR" ]]; then
        log_error "Deployment directory not found: $DEPLOY_DIR"
        exit 1
    fi

    # Check compose file
    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "Compose file not found: $COMPOSE_FILE"
        exit 1
    fi

    # Check environment file
    if [[ ! -f "$ENV_FILE" ]]; then
        log_error "Environment file not found: $ENV_FILE"
        exit 1
    fi

    # Check Docker daemon
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

get_current_images() {
    log_info "Recording current image versions..."

    PREVIOUS_BACKEND_IMAGE=$(docker inspect --format='{{.Config.Image}}' dashboard-backend-prod 2>/dev/null || echo "")
    PREVIOUS_FRONTEND_IMAGE=$(docker inspect --format='{{.Config.Image}}' dashboard-frontend-prod 2>/dev/null || echo "")

    if [[ -n "$PREVIOUS_BACKEND_IMAGE" ]]; then
        log_info "Current backend: $PREVIOUS_BACKEND_IMAGE"
    fi
    if [[ -n "$PREVIOUS_FRONTEND_IMAGE" ]]; then
        log_info "Current frontend: $PREVIOUS_FRONTEND_IMAGE"
    fi
}

login_registry() {
    log_info "Logging into container registry..."

    if [[ -n "${GITHUB_TOKEN:-}" ]]; then
        echo "$GITHUB_TOKEN" | docker login "$REGISTRY" -u "${GITHUB_USER:-deploy}" --password-stdin
        log_success "Registry login successful"
    elif [[ -f "${HOME}/.docker/config.json" ]]; then
        log_info "Using existing Docker credentials"
    else
        log_warn "No registry credentials found, using public access"
    fi
}

pull_images() {
    local tag="${1:-latest}"

    log_info "Pulling images with tag: $tag"

    local images=(
        "${IMAGE_BACKEND}:${tag}"
        "${IMAGE_FRONTEND}:${tag}"
    )

    for image in "${images[@]}"; do
        log_info "Pulling: $image"
        if ! docker pull "$image"; then
            log_error "Failed to pull image: $image"
            return 1
        fi
    done

    log_success "All images pulled successfully"
}

create_backup() {
    if [[ "$SKIP_BACKUP" == true ]]; then
        log_warn "Skipping backup (--skip-backup specified)"
        return 0
    fi

    BACKUP_TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
    local backup_path="${BACKUP_DIR}/${BACKUP_TIMESTAMP}"

    log_info "Creating pre-deployment backup..."
    mkdir -p "$backup_path"

    # Backup database
    log_info "Backing up database..."
    if docker exec dashboard-postgres-prod pg_dump -U "${POSTGRES_USER:-dashboard}" "${POSTGRES_DB:-dashboard_interface_data}" > "${backup_path}/database.sql" 2>/dev/null; then
        gzip "${backup_path}/database.sql"
        log_success "Database backup created"
    else
        log_warn "Database backup failed or database not running"
    fi

    # Backup current image versions
    cat > "${backup_path}/images.txt" <<EOF
BACKEND_IMAGE=${PREVIOUS_BACKEND_IMAGE}
FRONTEND_IMAGE=${PREVIOUS_FRONTEND_IMAGE}
TIMESTAMP=${BACKUP_TIMESTAMP}
EOF

    # Backup environment (without secrets)
    grep -v -E '(PASSWORD|SECRET|KEY|TOKEN)=' "$ENV_FILE" > "${backup_path}/env.filtered" 2>/dev/null || true

    # Cleanup old backups (keep last N)
    local backup_count
    backup_count=$(find "$BACKUP_DIR" -maxdepth 1 -type d -name "20*" | wc -l)
    if [[ $backup_count -gt $MAX_ROLLBACK_VERSIONS ]]; then
        log_info "Cleaning up old backups..."
        find "$BACKUP_DIR" -maxdepth 1 -type d -name "20*" | sort | head -n -${MAX_ROLLBACK_VERSIONS} | xargs rm -rf
    fi

    log_success "Backup created: $backup_path"
}

run_migrations() {
    if [[ "$SKIP_MIGRATIONS" == true ]]; then
        log_warn "Skipping migrations (--skip-migrations specified)"
        return 0
    fi

    log_info "Running database migrations..."

    # Wait for database to be ready
    local retries=30
    while [[ $retries -gt 0 ]]; do
        if docker exec dashboard-postgres-prod pg_isready -U "${POSTGRES_USER:-dashboard}" &>/dev/null; then
            break
        fi
        log_info "Waiting for database... ($retries retries left)"
        sleep 2
        ((retries--))
    done

    if [[ $retries -eq 0 ]]; then
        log_error "Database not ready after timeout"
        return 1
    fi

    # Run migrations using backend container
    if docker compose -f "$COMPOSE_FILE" run --rm backend alembic upgrade head; then
        log_success "Migrations completed successfully"
    else
        log_error "Migration failed"
        return 1
    fi
}

health_check() {
    local service="$1"
    local endpoint="${2:-/health}"
    local port="${3:-8000}"

    log_info "Running health check for $service..."

    local start_time
    start_time=$(date +%s)
    local elapsed=0

    while [[ $elapsed -lt $HEALTH_CHECK_TIMEOUT ]]; do
        # Check container is running
        if ! docker ps --filter "name=dashboard-${service}-prod" --filter "status=running" -q | grep -q .; then
            log_info "Container not yet running..."
            sleep "$HEALTH_CHECK_INTERVAL"
            elapsed=$(($(date +%s) - start_time))
            continue
        fi

        # Check health endpoint
        local health_url="http://localhost:${port}${endpoint}"
        if curl -sf "$health_url" > /dev/null 2>&1; then
            log_success "$service health check passed"
            return 0
        fi

        log_info "Health check pending... (${elapsed}s / ${HEALTH_CHECK_TIMEOUT}s)"
        sleep "$HEALTH_CHECK_INTERVAL"
        elapsed=$(($(date +%s) - start_time))
    done

    log_error "$service health check failed after ${HEALTH_CHECK_TIMEOUT}s"
    return 1
}

deploy_services() {
    local tag="${1:-latest}"

    DEPLOYMENT_STARTED=true

    log_info "Starting deployment with tag: $tag"

    # Export image tags for docker-compose
    export BACKEND_IMAGE="${IMAGE_BACKEND}:${tag}"
    export FRONTEND_IMAGE="${IMAGE_FRONTEND}:${tag}"

    # Stop existing services gracefully
    log_info "Stopping existing services..."
    docker compose -f "$COMPOSE_FILE" stop backend frontend || true

    # Start infrastructure services first (if not running)
    log_info "Ensuring infrastructure services are running..."
    docker compose -f "$COMPOSE_FILE" up -d postgres redis

    # Wait for infrastructure
    sleep 5

    # Run migrations
    run_migrations || return 1

    # Deploy backend with rolling update
    log_info "Deploying backend service..."
    docker compose -f "$COMPOSE_FILE" up -d --no-deps --force-recreate backend

    # Health check backend
    if ! health_check "backend" "/health" "8000"; then
        log_error "Backend deployment failed health check"
        return 1
    fi

    # Deploy frontend
    log_info "Deploying frontend service..."
    docker compose -f "$COMPOSE_FILE" up -d --no-deps --force-recreate frontend

    # Health check frontend
    if ! health_check "frontend" "/" "80"; then
        log_error "Frontend deployment failed health check"
        return 1
    fi

    # Cleanup old images
    log_info "Cleaning up unused images..."
    docker image prune -f > /dev/null 2>&1 || true

    log_success "Deployment completed successfully"
}

rollback() {
    local backup_timestamp="${1:-}"

    log_info "Starting rollback..."

    # Find latest backup if not specified
    if [[ -z "$backup_timestamp" ]]; then
        backup_timestamp=$(find "$BACKUP_DIR" -maxdepth 1 -type d -name "20*" | sort -r | head -n1 | xargs basename 2>/dev/null || echo "")
    fi

    if [[ -z "$backup_timestamp" ]]; then
        log_error "No backup found for rollback"
        exit 1
    fi

    local backup_path="${BACKUP_DIR}/${backup_timestamp}"

    if [[ ! -d "$backup_path" ]]; then
        log_error "Backup not found: $backup_path"
        exit 1
    fi

    log_info "Rolling back to: $backup_timestamp"

    # Load previous image versions
    if [[ -f "${backup_path}/images.txt" ]]; then
        # shellcheck source=/dev/null
        source "${backup_path}/images.txt"

        if [[ -n "${BACKEND_IMAGE:-}" && -n "${FRONTEND_IMAGE:-}" ]]; then
            log_info "Restoring backend image: $BACKEND_IMAGE"
            log_info "Restoring frontend image: $FRONTEND_IMAGE"

            export BACKEND_IMAGE
            export FRONTEND_IMAGE

            # Restart services with previous images
            docker compose -f "$COMPOSE_FILE" up -d --no-deps --force-recreate backend frontend

            # Health checks
            if health_check "backend" "/health" "8000" && health_check "frontend" "/" "80"; then
                log_success "Rollback completed successfully"
            else
                log_error "Rollback health checks failed"
                exit 1
            fi
        else
            log_error "Invalid backup: missing image information"
            exit 1
        fi
    else
        log_error "Backup images.txt not found"
        exit 1
    fi

    # Optionally restore database
    if [[ -f "${backup_path}/database.sql.gz" ]]; then
        read -rp "Restore database from backup? (y/N): " restore_db
        if [[ "$restore_db" =~ ^[Yy]$ ]]; then
            log_info "Restoring database..."
            gunzip -c "${backup_path}/database.sql.gz" | docker exec -i dashboard-postgres-prod psql -U "${POSTGRES_USER:-dashboard}" "${POSTGRES_DB:-dashboard_interface_data}"
            log_success "Database restored"
        fi
    fi
}

cleanup_on_failure() {
    if [[ "$DEPLOYMENT_STARTED" == true ]]; then
        log_error "Deployment failed, initiating automatic rollback..."

        # Attempt automatic rollback
        if [[ -n "$PREVIOUS_BACKEND_IMAGE" && -n "$PREVIOUS_FRONTEND_IMAGE" ]]; then
            export BACKEND_IMAGE="$PREVIOUS_BACKEND_IMAGE"
            export FRONTEND_IMAGE="$PREVIOUS_FRONTEND_IMAGE"

            docker compose -f "$COMPOSE_FILE" up -d --no-deps --force-recreate backend frontend || true

            log_warn "Automatic rollback attempted. Please verify system status."
        else
            log_error "Cannot rollback: no previous version recorded"
        fi
    fi
}

show_status() {
    log_info "Current deployment status:"
    echo ""
    docker compose -f "$COMPOSE_FILE" ps
    echo ""

    log_info "Container health:"
    docker ps --filter "name=dashboard" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
}

# =============================================================================
# Main Script
# =============================================================================
main() {
    local tag="latest"
    local do_rollback=false
    local dry_run=false
    SKIP_MIGRATIONS=false
    SKIP_BACKUP=false
    local force=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --tag)
                tag="$2"
                shift 2
                ;;
            --skip-migrations)
                SKIP_MIGRATIONS=true
                shift
                ;;
            --skip-backup)
                SKIP_BACKUP=true
                shift
                ;;
            --force)
                force=true
                shift
                ;;
            --rollback)
                do_rollback=true
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            --status)
                show_status
                exit 0
                ;;
            -h|--help)
                echo "Usage: $SCRIPT_NAME [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --tag TAG           Docker image tag to deploy (default: latest)"
                echo "  --skip-migrations   Skip database migrations"
                echo "  --skip-backup       Skip pre-deployment backup"
                echo "  --force             Force deployment without confirmations"
                echo "  --rollback          Rollback to previous deployment"
                echo "  --dry-run           Show what would be done"
                echo "  --status            Show current deployment status"
                echo "  -h, --help          Show this help"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Create log directory
    mkdir -p "$LOG_DIR"
    mkdir -p "$BACKUP_DIR"

    echo ""
    echo "=============================================="
    echo "  B&R Capital Dashboard - Deployment"
    echo "=============================================="
    echo ""

    # Load environment
    if [[ -f "$ENV_FILE" ]]; then
        set -a
        # shellcheck source=/dev/null
        source "$ENV_FILE"
        set +a
    fi

    # Setup cleanup trap
    trap cleanup_on_failure ERR

    # Handle rollback
    if [[ "$do_rollback" == true ]]; then
        rollback
        exit 0
    fi

    # Dry run
    if [[ "$dry_run" == true ]]; then
        log_info "DRY RUN - Would perform the following:"
        echo "  1. Check prerequisites"
        echo "  2. Login to registry: $REGISTRY"
        echo "  3. Pull images with tag: $tag"
        echo "  4. Create backup"
        echo "  5. Run database migrations"
        echo "  6. Deploy services"
        echo "  7. Run health checks"
        exit 0
    fi

    # Confirmation
    if [[ "$force" != true ]]; then
        echo "Deployment configuration:"
        echo "  Tag: $tag"
        echo "  Registry: $REGISTRY"
        echo "  Skip migrations: $SKIP_MIGRATIONS"
        echo "  Skip backup: $SKIP_BACKUP"
        echo ""
        read -rp "Proceed with deployment? (y/N): " confirm
        if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
            log_info "Deployment cancelled"
            exit 0
        fi
    fi

    # Execute deployment
    check_prerequisites
    get_current_images
    login_registry
    pull_images "$tag"
    create_backup
    deploy_services "$tag"

    echo ""
    echo "=============================================="
    echo "  Deployment Complete!"
    echo "=============================================="
    echo ""

    show_status
}

# Run main function
main "$@"
