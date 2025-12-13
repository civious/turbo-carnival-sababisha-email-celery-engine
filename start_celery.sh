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

# Clean up stale PID files
cleanup_pid_files() {
    echo "Cleaning up stale PID files..."
    rm -f /var/run/celery/*.pid
    rm -f /var/run/celery/beat.pid
}

start_worker() {
    local queue_name=$1
    local worker_name=$2
    local concurrency=$3
    
    echo "Starting Celery worker '$worker_name' for queue '$queue_name' with concurrency $concurrency..."
    
    # Remove existing PID file for this worker
    rm -f "/var/run/celery/${worker_name}.pid"
    
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
    
    # Remove existing beat PID file
    rm -f /var/run/celery/beat.pid
    
    celery -A $CELERY_APP beat \
        --loglevel=$LOG_LEVEL \
        --logfile=/var/log/celery/beat.log \
        --pidfile=/var/run/celery/beat.pid \
        --detach
}

stop_all() {
    echo "Stopping all Celery processes..."
    
    # Graceful shutdown using control
    celery -A $CELERY_APP control shutdown || true
    sleep 5
    
    # Force kill if still running
    pkill -f "celery -A $CELERY_APP" || true
    pkill -f "python.*celery" || true
    sleep 2
    
    # Clean up PID files
    cleanup_pid_files
}

check_workers() {
    echo "Checking worker status..."
    local max_attempts=5
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if celery -A $CELERY_APP inspect ping > /dev/null 2>&1; then
            echo "✅ Workers are responsive (attempt $attempt)"
            return 0
        else
            echo "⏳ Waiting for workers to respond... (attempt $attempt/$max_attempts)"
            sleep 2
            attempt=$((attempt + 1))
        fi
    done
    
    echo "❌ Workers not responding after $max_attempts attempts"
    return 1
}

status() {
    echo "🔍 Celery Status Check"
    echo "======================"
    
    echo -e "\n1. Process Check (with better detection):"
    # Use multiple patterns to catch all Celery processes
    CELERY_PROCESSES=$(ps aux | grep -E "(celery|python.*celery|tasks)" | grep -v grep || true)
    
    if [ -n "$CELERY_PROCESSES" ]; then
        echo "✅ Celery processes found:"
        echo "$CELERY_PROCESSES" | while read line; do
            # Extract PID and command
            PID=$(echo "$line" | awk '{print $2}')
            CMD=$(echo "$line" | awk '{$1=$2=$3=$4=$5=$6=$7=$8=$9=""; print $0}' | sed 's/^ *//')
            echo "   PID: $PID | Command: $CMD"
        done
        PROCESS_COUNT=$(echo "$CELERY_PROCESSES" | wc -l)
        echo "   Total processes: $PROCESS_COUNT"
    else
        echo "❌ No Celery processes found"
    fi
    
    echo -e "\n2. Worker Control Status:"
    if check_workers; then
        echo -e "\n📊 Queue Status:"
        celery -A $CELERY_APP inspect active_queues
        
        echo -e "\n📋 Registered Tasks:"
        celery -A $CELERY_APP inspect registered | head -20  # Show first 20 tasks
        
        echo -e "\n⚡ Active Tasks:"
        celery -A $CELERY_APP inspect active
        
        echo -e "\n⏰ Scheduled Tasks:"
        celery -A $CELERY_APP inspect scheduled
        
        echo -e "\n📈 Worker Stats:"
        celery -A $CELERY_APP inspect stats
    else
        echo "❌ Workers are not responding to control commands"
    fi
    
    echo -e "\n3. Log Files Check:"
    LOG_FILES=$(ls /var/log/celery/ 2>/dev/null || echo "No log files found")
    echo "Log files in /var/log/celery/:"
    echo "$LOG_FILES"
    
    echo -e "\n4. PID Files Check:"
    PID_FILES=$(ls /var/run/celery/*.pid 2>/dev/null | xargs -n 1 basename 2>/dev/null || echo "No PID files found")
    echo "PID files in /var/run/celery/:"
    echo "$PID_FILES"
}

case "${1:-}" in
    start)
        echo "Starting Celery services..."
        stop_all
        sleep 2
        start_worker "datagemail-queue" "email_worker" $WORKER_CONCURRENCY
        start_worker "log-queue" "log_worker" 1
        start_beat
        echo "All Celery services started"
        echo "Waiting for workers to initialize..."
        sleep 3
        check_workers
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
        echo "Restarting Celery services..."
        stop_all
        sleep 2
        start_worker "datagemail-queue" "email_worker" $WORKER_CONCURRENCY
        start_worker "log-queue" "log_worker" 1
        start_beat
        echo "All Celery services restarted"
        sleep 3
        check_workers
        ;;
    
    status)
        status
        ;;
    
    reload)
        echo "Sending HUP signal to reload workers..."
        pkill -HUP -f "celery -A $CELERY_APP" || true
        ;;
    
    logs)
        echo "Showing recent logs:"
        tail -f /var/log/celery/*.log
        ;;
    
    *)
        echo "Usage: $0 {start|start-email|start-log|start-beat|stop|restart|status|reload|logs}"
        echo ""
        echo "Commands:"
        echo "  start       - Start all Celery services"
        echo "  start-email - Start only email worker"
        echo "  start-log   - Start only log worker" 
        echo "  start-beat  - Start only beat scheduler"
        echo "  stop        - Stop all Celery services"
        echo "  restart     - Restart all Celery services"
        echo "  status      - Show detailed status of Celery processes"
        echo "  reload      - Reload workers (HUP signal)"
        echo "  logs        - Show live logs from all workers"
        echo ""
        echo "Environment Variables:"
        echo "  WORKER_CONCURRENCY - Number of worker processes (default: 2)"
        echo "  LOG_LEVEL          - Log level (default: info)"
        exit 1
        ;;
esac