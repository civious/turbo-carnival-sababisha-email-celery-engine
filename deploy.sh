#!/bin/bash
#
# Manual Deployment Script for Sababisha Celery Service
# This script can be used for manual deployments or testing
#

set -e  # Exit on error

# Configuration
DEPLOY_PATH="/opt/sababisha-celery"
PROJECT_NAME="sababisha-celery"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if running as root or with sudo
    if [ "$EUID" -eq 0 ]; then
        log_warn "Running as root - consider using a non-root user with sudo"
    fi

    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    # Check if Docker Compose is installed
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi

    # Check if Docker daemon is running
    if ! docker ps &> /dev/null; then
        log_error "Docker daemon is not running or not accessible"
        exit 1
    fi

    log_info "Prerequisites check passed"
}

setup_deploy_directory() {
    log_info "Setting up deployment directory..."

    # Create deployment directory if it doesn't exist
    if [ ! -d "$DEPLOY_PATH" ]; then
        log_info "Creating deployment directory: $DEPLOY_PATH"
        sudo mkdir -p "$DEPLOY_PATH"
        sudo chown -R $USER:$USER "$DEPLOY_PATH"
    fi

    # Check if .env file exists
    if [ ! -f "$DEPLOY_PATH/.env" ]; then
        log_warn ".env file not found at $DEPLOY_PATH/.env"

        if [ -f ".env" ]; then
            log_info "Copying .env from current directory"
            cp .env "$DEPLOY_PATH/.env"
        else
            log_error "No .env file found. Please create one before deploying."
            exit 1
        fi
    fi

    # Create Images directory if it doesn't exist
    if [ ! -d "$DEPLOY_PATH/Images" ]; then
        log_info "Creating Images directory"
        mkdir -p "$DEPLOY_PATH/Images"
    fi

    # Create logs directory
    mkdir -p "$DEPLOY_PATH/logs"

    log_info "Deployment directory setup complete"
}

stop_services() {
    log_info "Stopping running services..."

    cd "$DEPLOY_PATH" || exit 1

    if [ -f "docker-compose.yml" ]; then
        docker-compose down || true
    fi

    # Force remove containers if they exist
    docker rm -f sababisha-celery-email-worker sababisha-celery-log-worker sababisha-celery-beat 2>/dev/null || true

    log_info "Services stopped"
}

deploy_files() {
    log_info "Deploying application files..."

    # Copy application files
    rsync -av --exclude='.env' \
              --exclude='Images/' \
              --exclude='logs/' \
              --exclude='venv/' \
              --exclude='.git/' \
              --exclude='__pycache__/' \
              --exclude='*.pyc' \
              --exclude='celerybeat-schedule' \
              ./ "$DEPLOY_PATH/"

    # Set permissions
    chmod +x "$DEPLOY_PATH/start_celery.sh" 2>/dev/null || true

    log_info "Application files deployed"
}

build_images() {
    log_info "Building Docker images..."

    cd "$DEPLOY_PATH" || exit 1
    docker-compose build --no-cache

    log_info "Docker images built"
}

start_services() {
    log_info "Starting services..."

    cd "$DEPLOY_PATH" || exit 1
    docker-compose up -d

    # Wait for services to start
    sleep 10

    log_info "Services started"
}

verify_deployment() {
    log_info "Verifying deployment..."

    cd "$DEPLOY_PATH" || exit 1

    # Show container status
    echo ""
    echo "=== Container Status ==="
    docker-compose ps

    # Show recent logs
    echo ""
    echo "=== Recent Logs ==="
    docker-compose logs --tail=50

    echo ""
    log_info "Deployment verification complete"
}

# Main execution
main() {
    echo "=========================================="
    echo "Sababisha Celery Service Deployment"
    echo "=========================================="
    echo ""

    check_prerequisites
    setup_deploy_directory
    stop_services
    deploy_files
    build_images
    start_services
    verify_deployment

    echo ""
    echo "=========================================="
    log_info "Deployment completed successfully!"
    echo "=========================================="
    echo ""
    echo "Useful commands:"
    echo "  View logs:       cd $DEPLOY_PATH && docker-compose logs -f"
    echo "  Check status:    cd $DEPLOY_PATH && docker-compose ps"
    echo "  Restart:         cd $DEPLOY_PATH && docker-compose restart"
    echo "  Stop:            cd $DEPLOY_PATH && docker-compose down"
    echo ""
}

# Run main function
main
