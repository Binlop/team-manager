from core.exceptions import DomainError, NotFoundError

class TaskNotFoundError(NotFoundError):
    model_name = "Task"

class CommentNotFoundError(NotFoundError):
    model_name = "Comment"

class AssigneeNotInTeamError(DomainError):
    status_code = 409
    error_code = "assignee_not_in_team"
    
    def __init__(self, user_id: int, team_id: int):
        self.detail = f"Пользователь с ID {user_id} не является участником команды {team_id} и не может быть назначен исполнителем."
        super().__init__(self.detail)

class ScoreStatusMismatchError(DomainError):
    status_code = 409
    error_code = "score_status_mismatch"

    def __init__(self, score: float | None, status: str):
        self.detail = (
            f"Некорректная комбинация оценки и статуса: "
            f"score={score!r}, status={status!r}. "
            f"Оценка должна быть указана тогда и только тогда, когда статус — DONE."
        )
        super().__init__(self.detail)

class InvalidStatusTransitionError(DomainError):
    status_code = 409
    error_code = "invalid_status_transition"

    def __init__(self, current: str, target: str):
        self.detail = (
            f"Недопустимый переход статуса: {current!r} → {target!r}. "
            f"Разрешённые переходы из {current!r}: ..."
        )
        super().__init__(self.detail)