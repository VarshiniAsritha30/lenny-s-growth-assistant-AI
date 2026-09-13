import logging
import sys

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """Structured JSON logging. Never log secrets - callers pass only safe fields
    (request_id, session_id, operation, provider, model, latency_ms, status, ...).
    """
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=log_level)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(log_level)),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)


# Event name constants used across the app so log consumers can grep/alert on them.
class Events:
    REQUEST_STARTED = "request_started"
    REQUEST_COMPLETED = "request_completed"
    RETRIEVAL_COMPLETED = "retrieval_completed"
    MODEL_STARTED = "model_started"
    MODEL_COMPLETED = "model_completed"
    MODEL_FAILED = "model_failed"
    DATABASE_FAILED = "database_failed"
    ARTIFACT_CREATED = "artifact_created"
    ARTIFACT_RENDER_FAILED = "artifact_render_failed"
    INGESTION_CHUNK_STORED = "ingestion_chunk_stored"
    INGESTION_FAILED = "ingestion_failed"
