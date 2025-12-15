# Sababisha Celery Email Service - Deployment Guide

Complete guide for deploying the Sababisha Celery Email Service on a Debian server.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Server Setup](#initial-server-setup)
3. [Installation Methods](#installation-methods)
4. [Environment Configuration](#environment-configuration)
5. [Service Management](#service-management)
6. [Troubleshooting](#troubleshooting)
7. [CI/CD with Jenkins](#cicd-with-jenkins)

---

## Prerequisites

### Required Software

- **OS**: Debian/Ubuntu Linux
- **Python**: 3.12 or higher
- **Redis**: 6.x or higher (running on host or remote server)
- **Database**: Microsoft SQL Server (remote)
- **Git**: For code deployment

### Server Requirements

- Minimum 2GB RAM
- 10GB free disk space
- Network access to:
  - Redis server (172.22.240.1:6379)
  - MSSQL server (38.242.252.117:1418)
  - SMTP server (mail.datag.co.ke:465)

---

## Initial Server Setup

### 1. Install System Dependencies

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python 3.12 and required tools
sudo apt install python3.12 python3.12-venv python3-pip git -y

# Verify Python installation
python3.12 --version
```

### 2. Install Redis (if not using remote Redis)

```bash
# Install Redis server
sudo apt install redis-server -y

# Configure Redis to start on boot
sudo systemctl enable redis-server
sudo systemctl start redis-server

# Verify Redis is running
redis-cli ping  # Should return PONG
```

### 3. Create Application Directory

```bash
# Create application directory
sudo mkdir -p /opt/sababisha-celery

# Set ownership (adjust user as needed)
sudo chown -R $USER:$USER /opt/sababisha-celery

# Navigate to directory
cd /opt/sababisha-celery
```

---

## Installation Methods

You can deploy using either **Docker** or **Native systemd services**. Choose based on your requirements.

### Method 1: Docker Deployment (Recommended for Multi-Environment)

**Advantages:**

- Container isolation
- Easier dependency management
- Consistent across environments

**Setup Steps:**

```bash
# 1. Clone repository
cd /opt/sababisha-celery
git clone https://github.com/civious/turbo-carnival-sababisha-email-celery-engine.git .

# 2. Install Docker and Docker Compose
sudo apt install docker.io docker-compose -y
sudo systemctl enable docker
sudo systemctl start docker

# 3. Add user to docker group (optional, for non-root usage)
sudo usermod -aG docker $USER
# Log out and back in for group changes to take effect

# 4. Create .env file (see Environment Configuration section)
nano .env

# 5. Build and start services
docker-compose up -d

# 6. Verify services are running
docker-compose ps
docker-compose logs -f
```

**Docker Service Management:**

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart services
docker-compose restart

# View logs
docker-compose logs -f celery-beat
docker-compose logs -f celery-email-worker
docker-compose logs -f celery-log-worker

# Check status
docker-compose ps
```

### Method 2: Native Systemd Services (Recommended for Single Server)

**Advantages:**

- Lower resource usage
- Simpler setup
- Direct process execution

**Setup Steps:**

```bash
# 1. Clone repository
cd /opt/sababisha-celery
git clone https://github.com/civious/turbo-carnival-sababisha-email-celery-engine.git .

# 2. Create and activate virtual environment
python3.12 -m venv venv
source venv/bin/activate

# 3. Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Verify Celery installation
celery --version

# 5. Create .env file (see Environment Configuration section)
nano .env

# 6. Test Redis connection
python3 -c "import redis; r = redis.Redis(host='172.22.240.1', port=6379, password='MCBT3ChN0Log13s'); print(r.ping())"

# 7. Test database connection
python3 -c "from sqlalchemy import create_engine; engine = create_engine('mssql+pymssql://appollo:@mcbw3c0d3@d@y@38.242.252.117:1418/pos_shoes'); print(engine.connect())"

# 8. Install systemd services
cd systemd/native
sudo ./install-services.sh

# 9. Start services
sudo systemctl start sababisha-celery.target

# 10. Enable services to start on boot
sudo systemctl enable sababisha-celery.target

# 11. Verify services are running
sudo systemctl status sababisha-celery-*
```

**Native Service Management:**

```bash
# Start all services
sudo systemctl start sababisha-celery.target

# Stop all services
sudo systemctl stop sababisha-celery.target

# Restart all services
sudo systemctl restart sababisha-celery.target

# Check status of all services
sudo systemctl status sababisha-celery-*

# Check individual service status
sudo systemctl status sababisha-celery-beat
sudo systemctl status sababisha-celery-worker
sudo systemctl status sababisha-celery-log-worker

# View logs (real-time)
sudo journalctl -u sababisha-celery-beat -f
sudo journalctl -u sababisha-celery-worker -f
sudo journalctl -u sababisha-celery-log-worker -f

# View all service logs together
sudo journalctl -u sababisha-celery-* -f

# View last 100 lines of logs
sudo journalctl -u sababisha-celery-worker -n 100

# Restart individual service
sudo systemctl restart sababisha-celery-worker
```

---

## Environment Configuration

### Creating the .env File

**CRITICAL**: For systemd native services, the `.env` file must NOT have quotes around values.

**Important Notes:**

- NO quotes around values (systemd EnvironmentFile requirement)
- Empty values should be left blank (e.g., `REDIS_PASSWORD=` if no password)
- Passwords with special characters work without quotes
- File permissions: `sudo chmod 600 .env` for security

---

## Service Management

### Architecture Overview

The service consists of three components:

1. **Celery Beat** (sababisha-celery-beat)

   - Scheduler that triggers email scraping every 30 seconds
   - Reads unsent emails from database
   - Queues them for processing

2. **Email Worker** (sababisha-celery-worker)

   - Processes emails from the `celery` queue
   - Handles email sending via SMTP
   - Updates database status (SENT/FAILED)
   - Concurrency: 2 workers

3. **Log Worker** (sababisha-celery-log-worker)
   - Processes log tasks from `log-queue`
   - Handles error logging to database
   - Concurrency: 1 worker

### Service Files Location

**Native Services:**

- Service files: `/etc/systemd/system/sababisha-celery-*.service`
- Target file: `/etc/systemd/system/sababisha-celery.target`
- Source files: `/opt/sababisha-celery/systemd/native/`

**Docker Services:**

- Docker Compose: `/opt/sababisha-celery/docker-compose.yml`
- Dockerfile: `/opt/sababisha-celery/Dockerfile`

### Common Operations

#### Update Code and Restart

**For Native Services:**

```bash
cd /opt/sababisha-celery
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart sababisha-celery.target
```

**For Docker Services:**

```bash
cd /opt/sababisha-celery
git pull origin main
docker-compose down
docker-compose build
docker-compose up -d
```

#### View Real-Time Logs

**Native Services:**

```bash
# All services
sudo journalctl -u sababisha-celery-* -f

# Specific service
sudo journalctl -u sababisha-celery-worker -f
```

**Docker Services:**

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f celery-email-worker
```

#### Check Service Health

**Native Services:**

```bash
# Check if services are running
sudo systemctl is-active sababisha-celery-beat
sudo systemctl is-active sababisha-celery-worker
sudo systemctl is-active sababisha-celery-log-worker

# Detailed status
sudo systemctl status sababisha-celery.target
```

**Docker Services:**

```bash
# Check container status
docker-compose ps

# Check resource usage
docker stats
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Redis Connection Failed

**Error:** `Cannot connect to redis://localhost:6379/0: Authentication required`

**Cause:** Environment variables not loaded correctly (quotes in .env file)

**Solution:**

```bash
# Remove quotes from .env file
cd /opt/sababisha-celery
sed -i 's/="//g' .env
sed -i 's/"$//g' .env
sed -i 's/"//g' .env

# Restart services
sudo systemctl daemon-reload
sudo systemctl restart sababisha-celery.target
```

#### 2. Emails Sending But Not Marking as Sent

**Error:** Database not updating after email is sent successfully

**Cause:** SQLAlchemy session.commit() not persisting with pymssql driver

**Solution:** Already fixed in tasks.py using connection.commit() instead of session.commit()

**Verify Fix:**

```bash
# Check tasks.py has connection.commit()
grep -n "connection.commit()" /opt/sababisha-celery/tasks.py
```

#### 3. Service Fails to Start

**Check logs:**

```bash
sudo journalctl -u sababisha-celery-worker -n 50
```

**Common causes:**

- Virtual environment not found: Create at `/opt/sababisha-celery/venv`
- .env file missing: Create with proper configuration
- Dependencies not installed: `pip install -r requirements.txt`
- Redis not running: `sudo systemctl start redis`

#### 4. Tasks Not Being Scheduled

**Check Beat scheduler:**

```bash
sudo journalctl -u sababisha-celery-beat -f
```

**Should see:**

```
Scheduler: Sending due task scrape-unsent-emails-every-30-seconds
```

**If not:**

```bash
# Restart beat
sudo systemctl restart sababisha-celery-beat

# Check celery_config.py has correct schedule
cat /opt/sababisha-celery/celery_config.py | grep -A 5 "beat_schedule"
```

#### 5. Workers Not Processing Tasks

**Check queue status:**

```bash
cd /opt/sababisha-celery
source venv/bin/activate
celery -A celery_config:app inspect active_queues
celery -A celery_config:app inspect stats
```

**Check if workers are running:**

```bash
sudo systemctl status sababisha-celery-worker
sudo systemctl status sababisha-celery-log-worker
```

#### 6. Database Connection Issues

**Test connection:**

```bash
cd /opt/sababisha-celery
source venv/bin/activate
python3 << EOF
from sqlalchemy import create_engine, text
engine = create_engine('mssql+pymssql://appollo:@mcbw3c0d3@d@y@38.242.252.117:1418/pos_shoes')
with engine.connect() as conn:
    result = conn.execute(text("SELECT COUNT(*) FROM emailmessages WHERE statusflag = 0"))
    print(f"Unsent emails: {result.scalar()}")
EOF
```

#### 7. Permission Denied Errors

**Fix ownership:**

```bash
sudo chown -R root:root /opt/sababisha-celery
sudo chmod 755 /opt/sababisha-celery
sudo chmod 600 /opt/sababisha-celery/.env
```

#### 8. Module Not Found Errors

**Reinstall dependencies:**

```bash
cd /opt/sababisha-celery
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

#### 9. SMTP Authentication Failed

**Check SMTP credentials in .env:**

```bash
grep SMTP /opt/sababisha-celery/.env
```

**Test SMTP connection:**

```bash
python3 << EOF
import smtplib
smtp = smtplib.SMTP_SSL('mail.datag.co.ke', 465)
smtp.login('datag@datag.co.ke', 'MajyL?%H30K]')
print("SMTP connection successful")
smtp.quit()
EOF
```

---

## CI/CD with Jenkins

### Prerequisites

- Jenkins installed on the same server (no SSH needed)
- Git access to repository
- Jenkins user has sudo permissions for service restart

### Jenkins Setup

**1. Create Jenkins Pipeline Job:**

- Job name: `sababisha-celery-deploy`
- Type: Pipeline
- Pipeline script from SCM: Git
- Repository: `https://github.com/civious/turbo-carnival-sababisha-email-celery-engine.git`
- Branch: `main`
- Script path: `Jenkinsfile`

**2. Configure Build Triggers:**

- Poll SCM: `H/5 * * * *` (every 5 minutes)
- Or use GitHub webhooks for instant deployment

**3. Jenkins Environment Variables:**

```
DEPLOY_PATH=/opt/sababisha-celery
COMPOSE_PROJECT_NAME=sababisha-celery
```

### Jenkinsfile Configuration

The repository includes a Jenkinsfile that:

1. Checks out code from GitHub
2. Copies files to `/opt/sababisha-celery`
3. Restarts Docker Compose services or systemd services
4. Verifies deployment success

**For Native Services**, update the Jenkinsfile deploy stage:

```groovy
stage('Deploy') {
    steps {
        script {
            sh """
                cd ${DEPLOY_PATH}
                git pull origin main
                source venv/bin/activate
                pip install -r requirements.txt
                sudo systemctl restart sababisha-celery.target
            """
        }
    }
}
```

### Manual Deployment (Without Jenkins)

```bash
# 1. SSH to server
ssh user@your-server

# 2. Navigate to application directory
cd /opt/sababisha-celery

# 3. Pull latest code
git pull origin main

# 4. Update dependencies (for native services)
source venv/bin/activate
pip install -r requirements.txt

# 5. Restart services

# For Native Services:
sudo systemctl restart sababisha-celery.target

# For Docker Services:
docker-compose down
docker-compose build
docker-compose up -d

# 6. Verify deployment
sudo systemctl status sababisha-celery-*
# OR
docker-compose ps

# 7. Check logs
sudo journalctl -u sababisha-celery-worker -f
# OR
docker-compose logs -f
```

---

## Monitoring and Maintenance

### Log Rotation

Systemd handles journal rotation automatically, but you can configure:

```bash
# Edit journald config
sudo nano /etc/systemd/journald.conf

# Set limits
SystemMaxUse=1G
SystemKeepFree=500M
SystemMaxFileSize=100M

# Restart journald
sudo systemctl restart systemd-journald
```

### Health Checks

**Create monitoring script:**

```bash
cat > /opt/sababisha-celery/health_check.sh << 'EOF'
#!/bin/bash

echo "=== Sababisha Celery Health Check ==="
echo ""

# Check services
echo "Service Status:"
systemctl is-active sababisha-celery-beat && echo "✓ Beat is running" || echo "✗ Beat is DOWN"
systemctl is-active sababisha-celery-worker && echo "✓ Worker is running" || echo "✗ Worker is DOWN"
systemctl is-active sababisha-celery-log-worker && echo "✓ Log Worker is running" || echo "✗ Log Worker is DOWN"
echo ""

# Check Redis
echo "Redis Connection:"
redis-cli -h 172.22.240.1 -p 6379 -a MCBT3ChN0Log13s PING > /dev/null 2>&1 && echo "✓ Redis OK" || echo "✗ Redis FAILED"
echo ""

# Check queue lengths
echo "Queue Status:"
cd /opt/sababisha-celery
source venv/bin/activate
celery -A celery_config:app inspect active | grep -q "celery" && echo "✓ Workers active" || echo "✗ No active workers"
echo ""

# Check recent errors in logs
echo "Recent Errors (last 10 min):"
journalctl -u sababisha-celery-* --since "10 minutes ago" | grep -i error | wc -l
EOF

chmod +x /opt/sababisha-celery/health_check.sh

# Run health check
/opt/sababisha-celery/health_check.sh
```

### Backup and Recovery

**Backup critical files:**

```bash
# Create backup
tar -czf sababisha-celery-backup-$(date +%Y%m%d).tar.gz \
  /opt/sababisha-celery/.env \
  /opt/sababisha-celery/tasks.py \
  /opt/sababisha-celery/celery_config.py \
  /etc/systemd/system/sababisha-celery*

# Restore from backup
tar -xzf sababisha-celery-backup-YYYYMMDD.tar.gz -C /
sudo systemctl daemon-reload
sudo systemctl restart sababisha-celery.target
```

---

## Performance Tuning

### Adjusting Worker Concurrency

**For Native Services:**
Edit service file:

```bash
sudo nano /etc/systemd/system/sababisha-celery-worker.service

# Change concurrency
ExecStart=/opt/sababisha-celery/venv/bin/celery -A celery_config:app worker --queues=celery --concurrency=4 --hostname=email_worker@%h --loglevel=info

# Apply changes
sudo systemctl daemon-reload
sudo systemctl restart sababisha-celery-worker
```

**For Docker:**
Edit docker-compose.yml:

```yaml
celery-email-worker:
  command: celery -A celery_config:app worker --queues=celery --concurrency=4 --hostname=email_worker@%h --loglevel=info
```

### Beat Schedule Interval

Edit [celery_config.py](celery_config.py:82-88):

```python
app.conf.beat_schedule = {
    'scrape-unsent-emails-every-30-seconds': {
        'task': 'tasks.scrape_unsent_emails',
        'schedule': 60.0,  # Change to 60 seconds
        'options': {'queue': 'celery'}
    },
}
```

---

## Security Considerations

1. **Environment File Protection:**

   ```bash
   chmod 600 /opt/sababisha-celery/.env
   ```

2. **Firewall Configuration:**

   ```bash
   # Only allow Redis from specific IPs
   sudo ufw allow from 172.22.240.1 to any port 6379
   ```

3. **Service User (Optional):**
   Run services as non-root user:

   ```bash
   sudo useradd -r -s /bin/false sababisha-celery
   sudo chown -R sababisha-celery:sababisha-celery /opt/sababisha-celery

   # Update service files
   User=sababisha-celery
   Group=sababisha-celery
   ```

---

## Support and Contact

**For Issues or Questions:**

- **Developer:** Civious Rumaita
- **Phone:** 0715088150
- **Repository:** https://github.com/civious/turbo-carnival-sababisha-email-celery-engine.git

**Useful Commands Reference:**

```bash
# Check logs
sudo journalctl -u sababisha-celery-* -f

# Restart services
sudo systemctl restart sababisha-celery.target

# Check status
sudo systemctl status sababisha-celery-*

# Inspect Celery queues
celery -A celery_config:app inspect active_queues

# Purge all tasks (USE WITH CAUTION)
celery -A celery_config:app purge
```
