import time
import uuid
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from structlog.contextvars import bind_contextvars, clear_contextvars
import structlog

logger = structlog.get_logger("http.access")


class AccessLogMiddleware:
    """Access-log middleware in pure ASGI style (без BaseHTTPMiddleware).

    Чистый ASGI-медиатор вместо Starlette BaseHTTPMiddleware: исключения,
    возникающие ниже по стеку (в т.ч. обработанные ExceptionHandler'ами),
    не должны приводить к зависанию/завалу воркера.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        clear_contextvars()
        request_id = self._get_header(scope, "x-request-id") or str(uuid.uuid4())
        bind_contextvars(
            request_id=request_id,
            method=scope.get("method", ""),
            path=scope.get("path", ""),
            client=(scope.get("client") or [None, None])[0],
        )
        start_time = time.perf_counter()
        status_code = 0

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message.get("type") == "http.response.start":
                status_code = message.get("status", 0)
                headers = [
                    (k.lower(), v)
                    for k, v in message.get("headers") or []
                ]
                headers.append((b"x-request-id", request_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "request_finished",
                duration_ms=round(duration_ms, 2),
                status=status_code,
            )
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "request_failed",
                duration_ms=round(duration_ms, 2),
                exc_info=True,
            )
            raise
        finally:
            clear_contextvars()

    @staticmethod
    def _get_header(scope: Scope, name: str) -> str | None:
        target = name.lower().encode()
        for key, value in scope.get("headers") or []:
            if key.lower() == target:
                return value.decode()
        return None
