#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Define paths and defaults
VENV_PATH="/root/projects/DataGCeleryJobs/venv/bin"
APP_PATH="/root/projects/DataGCeleryJobs"
CELERY_APP="celery_config:app"
WORKER_CONCURRENCY="${WORKER_CONCURRENCY:-2}"
LOG_LEVEL="${LOG_LEVEL:-info}"
LOG_FILE="${LOG_FILE:-/var/log/celery/%n%I.log}"
PID_FILE="${PID_FILE:-/var/run/celery/%n.pid}"

# Check if virtual environment exists
if [ ! -f "$VENV_PATH/activate" ]; then
  echo "Error: Virtual environment not found at $VENV_PATH"
  exit 1
fi

# Activate the virtual environment
source "$VENV_PATH/activate"

# Change to app directory
cd "$APP_PATH" || {
  echo "Error: Failed to change directory to $APP_PATH"
  exit 1
}

# Create log and pid directories if they don't exist
mkdir -p /var/log/celery
mkdir -p /var/run/celery

start_worker() {
    local queue_name=$1
    local worker_name=$2
    local concurrency=$3
    
    echo "Starting Celery worker '$worker_name' for queue '$queue_name' with concurrency $concurrency..."
    
    celery -A $CELERY_APP worker \
        --queues=$queue_name \
        --concurrency=$concurrency \
        --hostname=$worker_name@%h \
        --loglevel=$LOG_LEVEL \
        --logfile=$LOG_FILE \
        --pidfile=$PID_FILE \
        --detach
}

start_beat() {
    echo "Starting Celery Beat scheduler..."
    
    celery -A $CELERY_APP beat \
        --loglevel=$LOG_LEVEL \
        --logfile=/var/log/celery/beat.log \
        --pidfile=/var/run/celery/beat.pid \
        --detach
}

stop_all() {
    echo "Stopping all Celery processes..."
    pkill -f "celery -A $CELERY_APP" || true
    sleep 2
}

status() {
    echo "Celery Processes:"
    ps aux | grep -E "celery -A $CELERY_APP" | grep -v grep || echo "No Celery processes running"
    
    echo -e "\nQueue Status:"
    celery -A $CELERY_APP inspect active_queues || echo "Could not inspect queues"
}

case "${1:-}" in
    start)
        stop_all
        start_worker "datagemail-queue" "email_worker" $WORKER_CONCURRENCY
        start_worker "log-queue" "log_worker" 1
        start_beat
        echo "All Celery services started"
        status
        ;;
    
    start-email)
        start_worker "datagemail-queue" "email_worker" $WORKER_CONCURRENCY
        ;;
    
    start-log)
        start_worker "log-queue" "log_worker" 1
        ;;
    
    start-beat)
        start_beat
        ;;
    
    stop)
        stop_all
        ;;
    
    restart)
        stop_all
        sleep 2
        start_worker "datagemail-queue" "email_worker" $WORKER_CONCURRENCY
        start_worker "log-queue" "log_worker" 1
        start_beat
        echo "All Celery services restarted"
        ;;
    
    status)
        status
        ;;
    
    reload)
        echo "Sending HUP signal to reload workers..."
        pkill -HUP -f "celery -A $CELERY_APP" || true
        ;;
    
    *)
        echo "Usage: $0 {start|start-email|start-log|start-beat|stop|restart|status|reload}"
        echo ""
        echo "Commands:"
        echo "  start       - Start all Celery services"
        echo "  start-email - Start only email worker"
        echo "  start-log   - Start only log worker" 
        echo "  start-beat  - Start only beat scheduler"
        echo "  stop        - Stop all Celery services"
        echo "  restart     - Restart all Celery services"
        echo "  status      - Show status of Celery processes"
        echo "  reload      - Reload workers (HUP signal)"
        echo ""
        echo "Environment Variables:"
        echo "  WORKER_CONCURRENCY - Number of worker processes (default: 2)"
        echo "  LOG_LEVEL          - Log level (default: info)"
        exit 1
        ;;
esac