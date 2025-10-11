import logging
import json
import time
import socket
from pythonjsonlogger import jsonlogger
import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
from obs_config import GrafanaConfig


class LokiLogHandler(logging.Handler):
    """Custom logging handler for Grafana Loki via requests"""

    def __init__(self, loki_url, username=None, password=None, tags=None):
        super().__init__()
        self.loki_url = loki_url.rstrip("/") + "/loki/api/v1/push"
        self.auth = HTTPBasicAuth(username, password) if username and password else None
        self.tags = tags or {}
        self.tags.update({
            "host": socket.gethostname(),
            "application": "email-service",
            "environment": GrafanaConfig.ENVIRONMENT
        })

    def emit(self, record):
        try:
            log_entry = self.format(record)
            labels = self.tags.copy()
            labels.update({
                "level": record.levelname,
                "service": getattr(record, "service", "unknown"),
                "task_id": getattr(record, "task_id", "unknown"),
            })

            payload = {
                "streams": [
                    {
                        "stream": labels,
                        "values": [
                            [str(int(record.created * 1e9)), log_entry]
                        ]
                    }
                ]
            }

            headers = {"Content-Type": "application/json"}
            response = requests.post(
                self.loki_url,
                data=json.dumps(payload),
                headers=headers,
                auth=self.auth,
                timeout=3
            )

            if not response.ok:
                print(f"Loki push failed: {response.status_code} - {response.text}")

        except Exception as e:
            print(f"Loki logging exception: {e}")


class ObservabilityLogger:
    """Enhanced logger with observability features"""

    def __init__(self, name):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)

        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s %(service)s %(task_id)s"
        )

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

        # Loki handler (optional)
        if GrafanaConfig.LOKI_URL:
            try:
                loki_handler = LokiLogHandler(
                    GrafanaConfig.LOKI_URL,
                    GrafanaConfig.LOKI_USERNAME,
                    GrafanaConfig.LOKI_PASSWORD,
                    tags={"service": "email-service"}
                )
                loki_handler.setFormatter(formatter)
                self.logger.addHandler(loki_handler)
            except Exception as e:
                print(f"Failed to initialize Loki handler: {e}")

        # Add default attributes
        self.logger = self._add_extra_attributes(self.logger)

    def _add_extra_attributes(self, logger):
        old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.service = "email-service"
            record.task_id = "unknown"
            return record

        logging.setLogRecordFactory(record_factory)
        return logger

    def set_task_id(self, task_id):
        old_factory = logging.getLogRecordFactory()

        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.service = "email-service"
            record.task_id = task_id
            return record

        logging.setLogRecordFactory(record_factory)

    # Convenience methods
    def info(self, msg, extra=None):
        self.logger.info(msg, extra=extra or {})

    def error(self, msg, extra=None, exc_info=True):
        self.logger.error(msg, extra=extra or {}, exc_info=exc_info)

    def warning(self, msg, extra=None):
        self.logger.warning(msg, extra=extra or {})

    def debug(self, msg, extra=None):
        self.logger.debug(msg, extra=extra or {})

    def critical(self, msg, extra=None):
        self.logger.critical(msg, extra=extra or {})


# Global instance
logger = ObservabilityLogger("email-service")
