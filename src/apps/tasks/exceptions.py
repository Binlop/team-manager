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