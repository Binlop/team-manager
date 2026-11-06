class DomainError(Exception):
    """Базовый тип ошибки."""
    status_code: int = 400
    error_code: str = "domain_error"

    def __init__(self, detail: str | None = None):
        self.detail = detail
        super().__init__(detail)

class NotFoundError(DomainError):
    model_name: str | None = None
    status_code = 404
    error_code = "not_found"

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if "model_name" not in cls.__dict__:
            raise TypeError(
                f"{cls.__name__} must define class attribute 'model_name'"
            )

    def __init__(self, model_object_id: int):
        self.model_object_id = model_object_id
        super().__init__(f"{self.model_name} with id={model_object_id} not found")

class PermissionDeniedError(DomainError):
    status_code = 403
    error_code = "permission_denied"
