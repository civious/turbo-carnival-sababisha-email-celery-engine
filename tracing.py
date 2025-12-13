from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
import os
from obs_config import GrafanaConfig

def setup_tracing():
    """Initialize distributed tracing with OpenTelemetry"""
    if not GrafanaConfig.OTEL_EXPORTER_OTLP_ENDPOINT:
        print("Tracing not configured - skipping tracing setup")
        return
    
    try:
        # Create resource
        resource = Resource.create({
            "service.name": GrafanaConfig.OTEL_SERVICE_NAME,
            "service.version": "1.0.0",
            "deployment.environment": GrafanaConfig.ENVIRONMENT,
        })
        
        # Set up tracer provider
        tracer_provider = TracerProvider(resource=resource)
        
        # Configure OTLP exporter
        otlp_exporter = OTLPSpanExporter(
            endpoint=GrafanaConfig.OTEL_EXPORTER_OTLP_ENDPOINT,
            headers={
                "Authorization": f"Basic {GrafanaConfig.OTEL_AUTH}"
            }
        )
        
        # Add span processor
        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor)
        
        # Set the global tracer provider
        trace.set_tracer_provider(tracer_provider)
        
        # Instrumentations
        CeleryInstrumentor().instrument(tracer_provider=tracer_provider)
        SQLAlchemyInstrumentor().instrument()
        RedisInstrumentor().instrument()
        LoggingInstrumentor().instrument()
        
        print("✅ OpenTelemetry tracing initialized")
        return tracer_provider
        
    except Exception as e:
        print(f"❌ Tracing setup failed: {e}")
        return None

def get_tracer():
    """Get tracer instance"""
    return trace.get_tracer(__name__)

def trace_task(func):
    """Decorator for tracing Celery tasks"""
    def wrapper(*args, **kwargs):
        tracer = get_tracer()
        with tracer.start_as_current_span(func.__name__) as span:
            span.set_attribute("task.name", func.__name__)
            span.set_attribute("service.name", "email-service")
            try:
                return func(*args, **kwargs)
            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
                raise
    return wrapper