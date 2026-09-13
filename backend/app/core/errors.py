from typing import Any

from fastapi import Request, status
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base class for application errors that map to a structured JSON error envelope.

    {"error": {"code": "...", "message": "...", "request_id": "...", "details": {...}}}
    """

    code: str = "INTERNAL_ERROR"
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ModelUnavailableError(AppError):
    code = "MODEL_UNAVAILABLE"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class ProviderConfigError(AppError):
    code = "PROVIDER_CONFIG_ERROR"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class DatabaseUnavailableError(AppError):
    code = "DATABASE_UNAVAILABLE"
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE


class NotFoundError(AppError):
    code = "NOT_FOUND"
    status_code = status.HTTP_404_NOT_FOUND


class InvalidRequestError(AppError):
    code = "INVALID_REQUEST"
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY


class ArtifactGenerationError(AppError):
    code = "ARTIFACT_GENERATION_FAILED"
    status_code = status.HTTP_502_BAD_GATEWAY


def error_response(request: Request, error: AppError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=error.status_code,
        content={
            "error": {
                "code": error.code,
                "message": error.message,
                "request_id": request_id,
                "details": error.details,
            }
        },
    )
