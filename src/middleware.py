import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from structlog.contextvars import bind_contextvars, clear_contextvars
import structlog
import uuid

logger = structlog.get_logger("http.access")

class AccessLogMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        clear_contextvars()
        request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
        bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else None,
        )
        start_time = time.perf_counter()
        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000 
            logger.info(
                "request_finished",
                duration_ms=round(duration_ms, 2),
                status=response.status_code,
            )
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000 
            logger.error(
                "request_failed",
                duration_ms=round(duration_ms, 2),
                exc_info=True,
            )
            raise 
        finally:
            clear_contextvars()