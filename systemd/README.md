# Systemd Service Installation Guide

This directory contains systemd service files for running the Sababisha Celery Email Service as a system service.

## Files

- `sababisha-celery.service` - Main service that starts all Docker containers
- `sababisha-celery-beat.service` - Celery beat scheduler service (individual)
- `sababisha-celery-worker.service` - Email worker service (individual)
- `sababisha-celery-log-worker.service` - Log worker service (individual)
- `install-services.sh` - Installation script

## Installation Steps

### 1. Deploy Your Application

First, ensure your application is deployed to `/opt/sababisha-celery`:

```bash
# If using Jenkins, trigger a deployment
# OR manually deploy:
cd /opt/sababisha-celery
git pull origin main
docker-compose build
```

### 2. Install the Services

```bash
cd /opt/sababisha-celery/systemd
sudo ./install-services.sh
```

This will:
- Copy service files to `/etc/systemd/system/`
- Reload systemd daemon
- Enable the service to start on boot

### 3. Start the Services

```bash
# Start all services
sudo systemctl start sababisha-celery

# Check status
sudo systemctl status sababisha-celery
```

## Service Management Commands

### Start/Stop/Restart

```bash
# Start all services
sudo systemctl start sababisha-celery

# Stop all services
sudo systemctl stop sababisha-celery

# Restart all services
sudo systemctl restart sababisha-celery

# Reload configuration (after changes)
sudo systemctl daemon-reload
sudo systemctl restart sababisha-celery
```

### Check Status

```bash
# Check if service is running
sudo systemctl status sababisha-celery

# Check all related services
sudo systemctl status sababisha-celery*
```

### View Logs

```bash
# View systemd logs
sudo journalctl -u sababisha-celery -f

# View Docker container logs
cd /opt/sababisha-celery
docker-compose logs -f

# View specific container logs
docker-compose logs -f celery-email-worker
docker-compose logs -f celery-beat
docker-compose logs -f celery-log-worker
```

### Enable/Disable Auto-Start

```bash
# Enable auto-start on boot (already done by install script)
sudo systemctl enable sababisha-celery

# Disable auto-start on boot
sudo systemctl disable sababisha-celery

# Check if enabled
sudo systemctl is-enabled sababisha-celery
```

## Service Architecture

The main service (`sababisha-celery.service`) uses `docker-compose` to manage all containers:

1. **celery-beat** - Scheduler that triggers email scraping every 30 seconds
2. **celery-email-worker** - Processes emails from the `celery` queue
3. **celery-log-worker** - Processes logs from the `log-queue` queue

All services will:
- Auto-start on server boot
- Auto-restart if they crash
- Log to systemd journal

## Troubleshooting

### Service Won't Start

```bash
# Check service status
sudo systemctl status sababisha-celery

# Check journal for errors
sudo journalctl -u sababisha-celery -n 50

# Check if Docker is running
sudo systemctl status docker

# Check if docker-compose is installed
which docker-compose
docker-compose --version
```

### Containers Not Running

```bash
# Check Docker containers
cd /opt/sababisha-celery
docker-compose ps

# Check Docker logs
docker-compose logs

# Manually start containers
docker-compose up -d
```

### Service Fails After Reboot

```bash
# Ensure service is enabled
sudo systemctl enable sababisha-celery

# Check service dependencies
sudo systemctl list-dependencies sababisha-celery

# Ensure Docker starts before Celery
sudo systemctl enable docker
```

### Update Service After Code Changes

```bash
# Option 1: Use Jenkins deployment (recommended)
# Trigger Jenkins build

# Option 2: Manual update
cd /opt/sababisha-celery
git pull origin main
docker-compose build
sudo systemctl restart sababisha-celery
```

## Uninstalling

```bash
# Stop and disable the service
sudo systemctl stop sababisha-celery
sudo systemctl disable sababisha-celery

# Remove service files
sudo rm /etc/systemd/system/sababisha-celery*.service

# Reload systemd
sudo systemctl daemon-reload
```

## Individual Service Control

If you need finer control, you can manage individual services:

```bash
# Restart only beat scheduler
sudo systemctl restart sababisha-celery-beat

# Restart only email worker
sudo systemctl restart sababisha-celery-worker

# Restart only log worker
sudo systemctl restart sababisha-celery-log-worker
```

## Monitoring

### Check if Service is Active

```bash
systemctl is-active sababisha-celery
```

### Check Service Uptime

```bash
systemctl show sababisha-celery --property=ActiveEnterTimestamp
```

### Monitor Resource Usage

```bash
# CPU and Memory usage
docker stats

# Specific container stats
docker stats sababisha-celery-email-worker
```

## Integration with Jenkins

The Jenkins pipeline will automatically rebuild and restart the containers. The systemd service will detect the restart and maintain the service state.

No manual systemd commands are needed after Jenkins deployment - the service will automatically pick up the changes when containers restart.

## Support

For issues or questions:
- **Contact:** Civious Rumaita
- **Phone:** 0715088150
- **Logs:** Check `/opt/sababisha-celery/logs/` and `journalctl -u sababisha-celery`
