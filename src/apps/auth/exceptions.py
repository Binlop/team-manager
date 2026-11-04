from core.exceptions import NotFoundError, DomainError

class InvalidCredentialsError(DomainError):
    """Неверный email или пароль."""
    status_code = 401
    error_code = "invalid_credentials"

class InvalidTokenError(DomainError):
    """Токен отсутствует, невалиден или истёк."""
    status_code = 401
    error_code = "invalid_token"

class EmailAlreadyExistsError(DomainError):
    """Email уже занят."""
    status_code = 409
    error_code = "email_already_exists"

    def __init__(self, email: str):
        self.email = email
        super().__init__(f"Email {email} already exists")


class UsernameAlreadyExistsError(DomainError):
    """Username уже занят."""
    status_code = 409
    error_code = "username_already_exists"

    def __init__(self, username: str):
        self.username = username
        super().__init__(f"Username {username} already exists")


class UserAlreadyDeletedError(DomainError):
    """Пользователь уже удалён."""
    status_code = 409
    error_code = "user_already_deleted"

    def __init__(self, user_id: int):
        self.user_id = user_id
        super().__init__(f"User {user_id} already deleted")


class UserNotFoundError(NotFoundError):
    model_name = "User"