import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import artifacts, feedback, health, messages, models, sessions, skills
from app.core.config import get_settings
from app.core.errors import AppError, error_response
from app.core.logging import Events, configure_logging, get_logger

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger(__name__)

app = FastAPI(title="The Lenny Growth Assistant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    request.state.request_id = request_id
    started = time.monotonic()

    logger.info(Events.REQUEST_STARTED, request_id=request_id, path=request.url.path, method=request.method)
    try:
        response = await call_next(request)
    except Exception:
        logger.error(Events.REQUEST_COMPLETED, request_id=request_id, path=request.url.path, status="error")
        raise

    latency_ms = int((time.monotonic() - started) * 1000)
    response.headers["x-request-id"] = request_id
    logger.info(
        Events.REQUEST_COMPLETED,
        request_id=request_id,
        path=request.url.path,
        status_code=response.status_code,
        latency_ms=latency_ms,
    )
    return response


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return error_response(request, exc)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "INVALID_REQUEST",
                "message": "Request validation failed.",
                "request_id": request_id,
                "details": {"errors": exc.errors()},
            }
        },
    )


app.include_router(health.router)
app.include_router(sessions.router)
app.include_router(messages.router)
app.include_router(skills.router)
app.include_router(artifacts.router)
app.include_router(models.router)
app.include_router(feedback.router)
