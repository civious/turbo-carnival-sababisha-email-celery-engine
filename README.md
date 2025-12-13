# DataG Celery Email Service

Automated email sending service using Celery with Redis broker.

## Features

- Automated email sending every 30 seconds
- Email encryption/decryption support
- Professional email footer with contact information
- OpenTelemetry tracing and Pyroscope profiling
- Docker containerized deployment
- Flower monitoring dashboard

## Project Structure

```
DataGCeleryJobs/
├── celery_config.py       # Celery configuration
├── tasks.py               # Task definitions
├── database.py            # Database connection
├── models.py              # SQLAlchemy models
├── loki_loghandler.py     # Logging handler
├── tracing.py             # OpenTelemetry tracing
├── profiling.py           # Pyroscope profiling
├── requirements.txt       # Python dependencies
├── Dockerfile             # Docker image definition
├── docker-compose.yml     # Multi-container setup
└── Images/
    └── logo.png          # Email footer logo
```

## Quick Start with Docker

### 1. Prerequisites

- Docker installed
- Docker Compose installed
- `.env` file configured (copy from `.env.example`)

**IMPORTANT SECURITY NOTE**: The `.env` file is mounted as a read-only volume and is NEVER copied into the Docker image. This ensures your credentials remain secure even if someone has access to the image.

### 2. Build and Run

```bash
# Build the Docker images
docker-compose build

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 3. Access Flower Monitoring

Open your browser to `http://localhost:5555` to monitor your Celery workers.

### 4. Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## Manual Setup (Without Docker)

### 1. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and update with your credentials.

### 3. Start Services

```bash
# Start Celery worker for email queue
./venv/bin/celery -A celery_config:app worker --queues=celery --concurrency=2 --loglevel=info

# Start Celery worker for log queue (in another terminal)
./venv/bin/celery -A celery_config:app worker --queues=log-queue --concurrency=1 --loglevel=info

# Start Celery beat scheduler (in another terminal)
./venv/bin/celery -A celery_config:app beat --loglevel=info
```

## Docker Commands

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f celery-email-worker
docker-compose logs -f celery-beat
docker-compose logs -f flower
```

### Restart Services

```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart celery-email-worker
```

### Execute Commands in Container

```bash
# Access container shell
docker-compose exec celery-email-worker bash

# Run debug script
docker-compose exec celery-email-worker python debug_celery.py

# Check worker status
docker-compose exec celery-email-worker celery -A celery_config:app inspect ping
```

### Scale Workers

```bash
# Scale email workers to 3 instances
docker-compose up -d --scale celery-email-worker=3
```

## Configuration

### Queue Routing

Tasks are routed to specific queues:
- `scrape_unsent_emails` → `celery` queue (email worker)
- `log_error` → `log-queue` queue (log worker)
- `health_check` → `log-queue` queue (log worker)

### Beat Schedule

- `scrape_unsent_emails`: Runs every 30 seconds

### Rate Limiting

- `scrape_unsent_emails`: 10 tasks per minute
- `send_email`: 30 tasks per minute

## Monitoring

### Flower Dashboard

Access at `http://localhost:5555`:
- View active workers
- Monitor task execution
- See task history
- View task stats

### Health Checks

Docker containers include health checks:
```bash
# Check container health
docker-compose ps
```

## Troubleshooting

### Workers Not Processing Tasks

1. Check worker status:
```bash
docker-compose exec celery-email-worker celery -A celery_config:app inspect ping
```

2. Check Redis connection:
```bash
docker-compose exec celery-email-worker python -c "from celery_config import get_redis_connection; r = get_redis_connection(); print(r.ping())"
```

3. Check queue lengths:
```bash
docker-compose exec celery-email-worker python debug_celery.py
```

### Email Sending Issues

1. Check SMTP configuration in `.env`
2. Verify encryption key is set
3. Check logs for detailed error messages

### Database Connection Issues

1. Verify MSSQL credentials in `.env`
2. Ensure database server is accessible from Docker network
3. Check if database driver is installed

## Support

For support, contact:
- **Civious Rumaita**
- **Phone**: 0715088150

## License

Private - Internal Use Only
