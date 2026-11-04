from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from core.exceptions import DomainError

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "detail": exc.detail,
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        errors = []
        for error in exc.errors():
            locs = [str(loc) for loc in error["loc"] if loc != "body"]
            field = " -> ".join(locs) if locs else "body"
            errors.append({"field": field, "message": error["msg"]})
            
        return JSONResponse(
            status_code=422,
            content={"error": "validation_error", "detail": errors},
        )