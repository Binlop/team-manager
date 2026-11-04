class DomainError(Exception):
    """Базовый тип ошибки."""
    status_code: int = 400
    error_code: str = "domain_error"

    def __init__(self, detail: str | None = None):
        self.detail = detail
        super().__init__(detail)

# class InvalidCredentialsError(DomainError):
#     """Неверный email или пароль."""
#     status_code = 401
#     error_code = "invalid_credentials"

# class InvalidTokenError(DomainError):
#     """Токен отсутствует, невалиден или истёк."""
#     status_code = 401
#     error_code = "invalid_token"

# class EmailAlreadyExistsError(DomainError):
#     """Email уже занят."""
#     status_code = 409
#     error_code = "email_already_exists"

#     def __init__(self, email: str):
#         self.email = email
#         super().__init__(f"Email {email} already exists")


# class UsernameAlreadyExistsError(DomainError):
#     """Username уже занят."""
#     status_code = 409
#     error_code = "username_already_exists"

#     def __init__(self, username: str):
#         self.username = username
#         super().__init__(f"Username {username} already exists")


# class UserAlreadyDeletedError(DomainError):
#     """Пользователь уже удалён."""
#     status_code = 409
#     error_code = "user_already_deleted"

#     def __init__(self, user_id: int):
#         self.user_id = user_id
#         super().__init__(f"User {user_id} already deleted")

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
