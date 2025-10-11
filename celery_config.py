from celery import Celery
from celery.schedules import crontab
import os
from dotenv import load_dotenv
import redis
from loki_loghandler import logger
load_dotenv()

# Parse Redis URL with password

redis_host = os.getenv('REDIS_HOST', 'localhost')
redis_port = int(os.getenv('REDIS_PORT', 6379))
redis_password = os.getenv('REDIS_PASSWORD', '')
redis_db = int(os.getenv('REDIS_DB', 0))

# Construct Redis URL with password
if redis_password:
    redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
else:
    redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"
# Celery app configuration with Redis authentication
app = Celery(
    'email_service',
    broker=redis_url,
    backend=redis_url,
    include=['email_tasks'],
    broker_connection_retry_on_startup=True
)

# Enhanced Redis configuration
app.conf.update(
    # Redis connection settings
    broker_use_ssl=False,
    redis_socket_keepalive=True,
    redis_socket_connect_timeout=5,
    redis_retry_on_timeout=True,
    broker_connection_retry=True,
    broker_connection_max_retries=3,
    
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Queue routing
    task_routes={
        'email_tasks.scrape_unsent_emails': {'queue': 'datagemail-queue'},
        'email_tasks.send_email': {'queue': 'datagemail-queue'},
        'email_tasks.send_email_with_file': {'queue': 'datagemail-queue'},
        'email_tasks.log_error': {'queue': 'log-queue'},
        'email_tasks.health_check': {'queue': 'log-queue'},
    },
    
    # Rate limiting
    task_annotations={
        'email_tasks.scrape_unsent_emails': {'rate_limit': '10/m'},
        'email_tasks.send_email': {'rate_limit': '30/m'},
    },
    
    # Retry settings
    task_default_retry_delay=30,
    task_max_retries=3,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # Redis backend settings
    result_backend_transport_options={
        'master_name': None,
        'retry_policy': {
            'timeout': 5.0
        }
    }
)

# Beat Schedule for periodic tasks
app.conf.beat_schedule = {
    'scrape-unsent-emails-every-10-seconds': {
        'task': 'email_tasks.scrape_unsent_emails',
        'schedule': 10.0,
        'options': {'queue': 'datagemail-queue'}
    },
}

# Custom Redis connection for direct access (optional)
def get_redis_connection():
    """Get authenticated Redis connection for direct operations"""
    try:
        if redis_password:
            # For Redis with password
            return redis.Redis(
                host=os.getenv('REDIS_HOST', 'localhost'),
                port=int(os.getenv('REDIS_PORT', 6379)),
                password=redis_password,
                db=int(os.getenv('REDIS_DB', 0)),
                decode_responses=True,
                socket_connect_timeout=5,
                retry_on_timeout=True
            )
        else:
            # For Redis without password
            return redis.from_url(redis_url, decode_responses=True)
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise

