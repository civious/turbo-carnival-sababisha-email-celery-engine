# Deployment Guide - Sababisha Celery Service

This guide covers deploying the Sababisha Celery email service to a Debian server using Jenkins.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Jenkins Setup](#jenkins-setup)
- [Deployment Process](#deployment-process)
- [Manual Deployment](#manual-deployment)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### On Debian Server

1. **Docker & Docker Compose**
   ```bash
   # Install Docker
   curl -fsSL https://get.docker.com -o get-docker.sh
   sudo sh get-docker.sh

   # Install Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

2. **Jenkins User Docker Access**
   ```bash
   # Add jenkins user to docker group
   sudo usermod -aG docker jenkins

   # Restart Jenkins
   sudo systemctl restart jenkins
   ```

3. **Deployment Directory Setup**
   ```bash
   # Create deployment directory
   sudo mkdir -p /opt/sababisha-celery
   sudo chown -R jenkins:jenkins /opt/sababisha-celery

   # Create .env file with credentials
   sudo nano /opt/sababisha-celery/.env
   # Copy contents from .env.example and update with real values
   ```

4. **Required Tools**
   ```bash
   # Install rsync
   sudo apt-get update
   sudo apt-get install -y rsync
   ```

---

## Jenkins Setup

### 1. Create Jenkins Pipeline Job

1. Go to Jenkins Dashboard
2. Click "New Item"
3. Enter name: `sababisha-celery-deploy`
4. Select "Pipeline"
5. Click "OK"

### 2. Configure Pipeline

**General Settings:**
- ✅ Discard old builds (keep last 10)
- Description: "Deploy Sababisha Celery Email Service"

**Build Triggers:**
- ✅ Poll SCM (optional): `H/5 * * * *` (checks every 5 minutes)
- ✅ GitHub hook trigger (if using GitHub)

**Pipeline Settings:**
- Definition: `Pipeline script from SCM`
- SCM: `Git`
- Repository URL: `https://github.com/civious/turbo-carnival-sababisha-email-celery-engine.git`
- Credentials: Add your GitHub credentials (if private repo)
- Branch: `*/main`
- Script Path: `Jenkinsfile`

### 3. Environment Variables (Optional)

In Pipeline configuration, you can override these variables:

```groovy
environment {
    DEPLOY_PATH = '/opt/sababisha-celery'
    GIT_BRANCH = 'main'
}
```

### 4. Jenkins Credentials Setup

**Repository:** `https://github.com/civious/turbo-carnival-sababisha-email-celery-engine.git`

If your repository is private:

1. Go to "Manage Jenkins" → "Credentials"
2. Click "Add Credentials"
3. Select "Username with password"
4. Enter your GitHub username and Personal Access Token (PAT)
5. ID: `github-civious` (or any identifier)
6. Select these credentials in Pipeline configuration

**Generate GitHub PAT:**
1. Go to GitHub → Settings → Developer settings → Personal access tokens
2. Generate new token with `repo` scope
3. Copy token and use as password in Jenkins

---

## Deployment Process

### Automated Deployment (via Jenkins)

1. **Trigger Build:**
   - Click "Build Now" in Jenkins job
   - Or push to main branch (if GitHub webhook configured)

2. **Monitor Progress:**
   - Click on build number
   - View "Console Output" for real-time logs

3. **Pipeline Stages:**
   ```
   1. Cleanup Workspace      - Clean Jenkins workspace
   2. Checkout               - Get code from Git
   3. Verify Environment     - Check prerequisites
   4. Stop Running Containers- Stop old services
   5. Deploy Application     - Copy new files
   6. Build Docker Images    - Build containers
   7. Start Services         - Start Celery workers
   8. Health Check           - Verify services running
   9. Verify Deployment      - Final checks
   ```

### What Gets Deployed

**Files Copied:**
- All Python source code
- `Dockerfile`
- `docker-compose.yml`
- `requirements.txt`
- Configuration files

**Files NOT Copied (for security):**
- `.env` (must exist on server already)
- `Images/` (must exist on server)
- `venv/` (not needed in Docker)
- `.git/` (not needed in production)
- Log files

---

## Manual Deployment

If you need to deploy manually without Jenkins:

### Option 1: Using deploy.sh Script

```bash
# On your Debian server
cd /path/to/your/code
./deploy.sh
```

### Option 2: Step-by-Step Manual Deployment

```bash
# 1. Stop running services
cd /opt/sababisha-celery
docker-compose down

# 2. Update code (if using Git on server)
git pull origin main

# Or copy files manually
rsync -av --exclude='.env' --exclude='Images/' /source/path/ /opt/sababisha-celery/

# 3. Build images
docker-compose build --no-cache

# 4. Start services
docker-compose up -d

# 5. Check status
docker-compose ps
docker-compose logs -f
```

---

## Post-Deployment

### Verify Services Are Running

```bash
cd /opt/sababisha-celery

# Check container status
docker-compose ps

# View logs
docker-compose logs -f

# Check specific service
docker-compose logs -f celery-email-worker
```

### Check Worker Health

```bash
# Ping workers
docker-compose exec celery-email-worker celery -A celery_config:app inspect ping

# Check active tasks
docker-compose exec celery-email-worker celery -A celery_config:app inspect active

# Check queue status
docker-compose exec celery-email-worker celery -A celery_config:app inspect stats
```

---

## Troubleshooting

### Jenkins Fails with Permission Denied

```bash
# Add jenkins user to docker group
sudo usermod -aG docker jenkins

# Restart Jenkins
sudo systemctl restart jenkins
```

### .env File Missing Error

```bash
# Create .env file in deployment directory
sudo nano /opt/sababisha-celery/.env

# Copy from .env.example and update values
```

### Containers Not Starting

```bash
# Check Docker logs
docker-compose logs

# Check if ports are in use
sudo netstat -tulpn | grep 6379  # Redis port

# Check if .env is mounted correctly
docker-compose exec celery-email-worker cat /app/.env
```

### Workers Not Processing Tasks

```bash
# Check Redis connection
docker-compose exec celery-email-worker python -c "
from celery_config import get_redis_connection
r = get_redis_connection()
print(r.ping())
"

# Check queue lengths
docker-compose exec celery-email-worker python debug_celery.py
```

### Image/Logo Not Found

```bash
# Ensure Images directory exists
mkdir -p /opt/sababisha-celery/Images

# Copy logo file
cp logo.png /opt/sababisha-celery/Images/

# Check permissions
ls -la /opt/sababisha-celery/Images/
```

### Rolling Back Deployment

```bash
cd /opt/sababisha-celery

# Stop current services
docker-compose down

# Checkout previous version (if using Git)
git checkout <previous-commit-hash>

# Or restore from backup
rsync -av /backup/path/ /opt/sababisha-celery/

# Rebuild and restart
docker-compose build
docker-compose up -d
```

---

## Monitoring & Maintenance

### View Real-time Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f celery-email-worker

# Last 100 lines
docker-compose logs --tail=100
```

### Restart Services

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart celery-email-worker

# Restart with rebuild
docker-compose down
docker-compose build
docker-compose up -d
```

### Update Environment Variables

```bash
# Edit .env
nano /opt/sababisha-celery/.env

# Restart services to apply changes
docker-compose restart
```

---

## Security Notes

1. **Never commit `.env` file to Git**
2. **`.env` is mounted as volume, not in image** - Safe to share Docker image
3. **Keep `.env` file permissions restricted:**
   ```bash
   chmod 600 /opt/sababisha-celery/.env
   chown jenkins:jenkins /opt/sababisha-celery/.env
   ```

---

## Support

For issues or questions:
- **Contact:** Civious Rumaita
- **Phone:** 0715088150
- **Check logs:** `/opt/sababisha-celery/logs/`

---

## Quick Reference

### Common Commands

| Action | Command |
|--------|---------|
| View status | `cd /opt/sababisha-celery && docker-compose ps` |
| View logs | `cd /opt/sababisha-celery && docker-compose logs -f` |
| Restart | `cd /opt/sababisha-celery && docker-compose restart` |
| Stop | `cd /opt/sababisha-celery && docker-compose down` |
| Start | `cd /opt/sababisha-celery && docker-compose up -d` |
| Rebuild | `cd /opt/sababisha-celery && docker-compose build` |

### Important Paths

| Item | Path |
|------|------|
| Deployment directory | `/opt/sababisha-celery` |
| Environment file | `/opt/sababisha-celery/.env` |
| Logo images | `/opt/sababisha-celery/Images/` |
| Logs | `/opt/sababisha-celery/logs/` |
| Jenkins workspace | `/var/lib/jenkins/workspace/sababisha-celery-deploy/` |
