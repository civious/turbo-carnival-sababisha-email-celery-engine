import pyroscope
import os
from obs_config import GrafanaConfig

def setup_pyroscope():
    """Initialize Pyroscope continuous profiling"""
    if not GrafanaConfig.PYROSCOPE_URL:
        print("Pyroscope not configured - skipping profiling setup")
        return
    
    try:
        pyroscope.configure(
            application_name=GrafanaConfig.PYROSCOPE_APPLICATION_NAME,
            server_address=GrafanaConfig.PYROSCOPE_URL,
            basic_auth_username = GrafanaConfig.PYROSCOPE_USER,
            basic_auth_password=GrafanaConfig.PYROSCOPE_PASSWORD,
            tags={
                "environment": GrafanaConfig.ENVIRONMENT,
                "host": os.uname().nodename,
                "service": "email-service"
            },
            detect_subprocesses=True,
            oncpu=True,
            native=True,
        )
        print("✅ Pyroscope profiling initialized")
    except Exception as e:
        print(f"❌ Pyroscope setup failed: {e}")

def profile_task(func):
    """Decorator for profiling Celery tasks"""
    def wrapper(*args, **kwargs):
        if GrafanaConfig.PYROSCOPE_URL:
            # Create a profiling context for this task
            task_name = func.__name__
            with pyroscope.tag_wrapper({"task": task_name}):
                return func(*args, **kwargs)
        else:
            return func(*args, **kwargs)
    return wrapper