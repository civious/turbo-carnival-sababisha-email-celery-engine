import os
from dotenv import load_dotenv

load_dotenv()

class GrafanaConfig:
    # Loki Configuration
    LOKI_URL = os.getenv('GRAFANA_LOKI_URL', '')
    LOKI_USERNAME = os.getenv('GRAFANA_USERNAME', '')
    LOKI_PASSWORD = os.getenv('GRAFANA_PASSWORD', '')


    
    # Pyroscope Configuration
    PYROSCOPE_URL = os.getenv('GRAFANA_PYROSCOPE_URL', '')
    PYROSCOPE_APPLICATION_NAME = os.getenv('PYROSCOPE_APPLICATION_NAME', 'celery-email-service')
    PYROSCOPE_USER= os.getenv('PYRO_USER')
    PYROSCOPE_PASSWORD= os.getenv('PYRO_PASS')
    
    # Tempo/Tracing Configuration
    OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT', '')
    OTEL_SERVICE_NAME = os.getenv('OTEL_SERVICE_NAME', 'email-service')
    OTEL_AUTH=os.getenv('OTEL_AUTH')
    
    # Environment
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

class AppConfig:
    # Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Database
    MSSQL_SERVER = os.getenv('MSSQL_SERVER')
    MSSQL_DATABASE = os.getenv('MSSQL_DATABASE')
    MSSQL_USERNAME = os.getenv('MSSQL_USERNAME')
    MSSQL_PASSWORD = os.getenv('MSSQL_PASSWORD')
    
    # Email
    SMTP_SERVER = os.getenv('SMTP_SERVER')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 465))
    SMTP_USERNAME = os.getenv('SMTP_USERNAME')
    SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')