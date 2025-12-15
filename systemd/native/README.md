# Native Systemd Service (Without Docker)

This directory contains systemd service files for running the Sababisha Celery Email Service **natively** (without Docker).

## Comparison: Docker vs Native

| Feature | Docker (parent directory) | Native (this directory) |
|---------|--------------------------|-------------------------|
| **Dependencies** | Requires Docker & Docker Compose | Only requires Python & virtual environment |
| **Resource Usage** | Higher (Docker overhead) | Lower (runs directly) |
| **Isolation** | Full container isolation | Process-level isolation only |
| **Deployment** | Jenkins builds Docker images | Jenkins copies files, restarts services |
| **Complexity** | More complex (Docker layers) | Simpler (direct execution) |
| **Recommended For** | Production with multiple environments | Single server, simpler setup |

## Prerequisites

Before installation, ensure you have:

1. **Python 3.12** installed
2. **Virtual environment** created at `/opt/sababisha-celery/venv`
3. **Dependencies** installed in the virtual environment
4. **Redis server** running
5. **`.env` file** configured at `/opt/sababisha-celery/.env`

### Setup Prerequisites

```bash
# 1. Install Python 3.12 (if not installed)
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip -y

# 2. Create virtual environment
cd /opt/sababisha-celery
python3.12 -m venv venv

# 3. Install dependencies
source venv/bin/activate
pip install -r requirements.txt

# 4. Ensure .env file exists
ls -la .env

# 5. Ensure Redis is running
systemctl status redis
# OR
redis-cli ping
```

## Installation

```bash
cd /opt/sababisha-celery/systemd/native
sudo ./install-services.sh
```

## Service Management

### Start All Services

```bash
sudo systemctl start sababisha-celery.target
```

### Check Status

```bash
# Check all services
sudo systemctl status sababisha-celery-*

# Check individual services
sudo systemctl status sababisha-celery-beat
sudo systemctl status sababisha-celery-worker
sudo systemctl status sababisha-celery-log-worker
```

### View Logs

```bash
# Beat scheduler logs
sudo journalctl -u sababisha-celery-beat -f

# Email worker logs
sudo journalctl -u sababisha-celery-worker -f

# Log worker logs
sudo journalctl -u sababisha-celery-log-worker -f

# All services (combined)
sudo journalctl -u sababisha-celery-* -f
```

### Restart Services

```bash
# Restart all
sudo systemctl restart sababisha-celery.target

# Restart individual services
sudo systemctl restart sababisha-celery-beat
sudo systemctl restart sababisha-celery-worker
sudo systemctl restart sababisha-celery-log-worker
```

### Stop Services

```bash
sudo systemctl stop sababisha-celery.target
```

## Service Architecture

Three independent services managed by a target:

1. **sababisha-celery-beat.service** - Celery Beat scheduler
2. **sababisha-celery-worker.service** - Email queue worker (2 concurrent)
3. **sababisha-celery-log-worker.service** - Log queue worker (1 concurrent)
4. **sababisha-celery.target** - Target to control all services together

## Environment Variables

Services load environment variables from `/opt/sababisha-celery/.env` using `EnvironmentFile`.

**Important:** Systemd doesn't support `.env` file format with quotes. Format your `.env` like this:

```bash
# WRONG (don't use quotes in systemd)
REDIS_HOST="172.22.240.1"

# CORRECT (no quotes)
REDIS_HOST=172.22.240.1
```

If your `.env` has quotes, create a separate `systemd.env` file without quotes.

## Troubleshooting

### Service Fails to Start

```bash
# Check service status
sudo systemctl status sababisha-celery-worker

# View detailed logs
sudo journalctl -u sababisha-celery-worker -n 100

# Check if virtual environment works
/opt/sababisha-celery/venv/bin/python --version
/opt/sababisha-celery/venv/bin/celery --version
```

### Environment Variables Not Loading

```bash
# Test if .env is being read
sudo systemctl show sababisha-celery-worker | grep Environment

# Manually test the service command
cd /opt/sababisha-celery
source .env
source venv/bin/activate
celery -A celery_config:app worker --queues=celery --loglevel=debug
```

### Python Module Not Found

```bash
# Ensure all dependencies are installed
cd /opt/sababisha-celery
source venv/bin/activate
pip install -r requirements.txt
```

### Permission Denied

```bash
# Ensure proper ownership
sudo chown -R root:root /opt/sababisha-celery
sudo chmod -R 755 /opt/sababisha-celery

# Ensure .env is readable
sudo chmod 644 /opt/sababisha-celery/.env
```

## Updating After Code Changes

### Option 1: Jenkins Deployment

If using Jenkins, update the Jenkinsfile to restart services instead of Docker containers:

```groovy
// In Jenkinsfile, replace docker-compose commands with:
sh 'sudo systemctl restart sababisha-celery.target'
```

### Option 2: Manual Update

```bash
cd /opt/sababisha-celery
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart sababisha-celery.target
```

## Uninstalling

```bash
# Stop and disable services
sudo systemctl stop sababisha-celery.target
sudo systemctl disable sababisha-celery-beat.service
sudo systemctl disable sababisha-celery-worker.service
sudo systemctl disable sababisha-celery-log-worker.service
sudo systemctl disable sababisha-celery.target

# Remove service files
sudo rm /etc/systemd/system/sababisha-celery*.{service,target}

# Reload systemd
sudo systemctl daemon-reload
```

## Support

For issues or questions:
- **Contact:** Civious Rumaita
- **Phone:** 0715088150
- **Logs:** `sudo journalctl -u sababisha-celery-* -f`
