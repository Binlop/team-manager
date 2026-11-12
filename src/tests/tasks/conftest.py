"""
Общие фикстуры для тестов репозиториев tasks.

Положи файл в src/tests/tasks/conftest.py.
Использует фикстуры из корневого conftest: session, uow, user_factory.

Файл самодостаточен (make_user/make_team/make_member дублируют фикстуры из
tests/teams/conftest.py). Если надоест дублирование, перенеси общие фикстуры
в src/tests/conftest.py.

ВАЖНО: не добавляй __init__.py в src/tests/tasks, иначе папка снова
перекроет настоящий пакет tasks.
"""
import itertools
from datetime import date, datetime, time, timedelta
from types import SimpleNamespace

import pytest
import pytest_asyncio

from tasks.models import Comment, Task
from teams.models import Team, TeamMember, TeamRole

# Срок задачи (due_date) - это дата, поэтому тесты работают с днями, а не с часами.
D0 = date(2030, 1, 1)

_counter = itertools.count(1)


@pytest.fixture
def day():
    """day(2) -> 2030-01-03 (дата, D0 + 2 дня)."""

    def _day(n: int) -> date:
        return D0 + timedelta(days=n)

    return _day


@pytest.fixture
def day_dt():
    """day_dt(2) -> полночь 2030-01-03 (datetime для параметров окна)."""

    def _day_dt(n: int) -> datetime:
        return datetime.combine(D0 + timedelta(days=n), time())

    return _day_dt


@pytest.fixture
def detach(session):
    """
    Сбрасывает identity map, чтобы репозиторий загрузил объекты заново.
    Так проверяется, что joinedload/selectinload действительно подгрузили
    связи: в async-сессии ленивая загрузка бросила бы MissingGreenlet.
    """

    async def _detach() -> None:
        await session.flush()
        session.expunge_all()

    return _detach


@pytest.fixture
def make_user(user_factory):
    """user_factory с уникальными username/email."""

    async def _make():
        n = next(_counter)
        return await user_factory(username=f"user{n}", email=f"user{n}@example.com")

    return _make


@pytest.fixture
def make_team(session, make_user):
    """Команда с менеджером. По умолчанию менеджер НЕ добавляется в участники."""

    async def _make(manager=None, with_manager_member: bool = False) -> Team:
        manager = manager or await make_user()
        n = next(_counter)
        team = Team(name=f"Team {n}", invite_code=f"invite-{n}", manager_id=manager.id)
        session.add(team)
        await session.flush()
        if with_manager_member:
            session.add(
                TeamMember(user_id=manager.id, team_id=team.id, role=TeamRole.MANAGER)
            )
            await session.flush()
        return team

    return _make


@pytest.fixture
def make_member(session):
    async def _make(user, team, role=TeamRole.MEMBER) -> TeamMember:
        member = TeamMember(user_id=user.id, team_id=team.id, role=role)
        session.add(member)
        await session.flush()
        return member

    return _make


@pytest.fixture
def make_task(session, day):
    """
    due_d - срок в днях от 2030-01-01 (None = без срока).
    status передаётся в модель только если указан (иначе берётся дефолт модели).
    """

    async def _make(
        team,
        assignee=None,
        title: str | None = None,
        due_d: int | None = None,
        score: int | None = None,
        status=None,
    ) -> Task:
        extra = {} if status is None else {"status": status}
        task = Task(
            title=title or f"Task {next(_counter)}",
            description="description",
            due_date=None if due_d is None else day(due_d),
            assignee_id=None if assignee is None else assignee.id,
            team_id=team.id,
            score=score,
            **extra,
        )
        session.add(task)
        await session.flush()
        return task

    return _make


@pytest.fixture
def make_comment(session):
    async def _make(task, author, description: str | None = None) -> Comment:
        comment = Comment(
            description=description or f"Comment {next(_counter)}",
            author_id=author.id,
            task_id=task.id,
        )
        session.add(comment)
        await session.flush()
        return comment

    return _make


@pytest_asyncio.fixture
async def scene(make_user, make_team, make_member, make_task):
    """
    Типовая расстановка для проверки доступа к задаче:

      team      - команда, менеджер manager (в участниках НЕ числится)
      member    - обычный участник команды
      assignee  - исполнитель задачи (НЕ участник команды)
      stranger  - посторонний: не исполнитель, не участник, не менеджер
      task      - задача команды team, исполнитель assignee, без срока
    """
    manager = await make_user()
    member = await make_user()
    assignee = await make_user()
    stranger = await make_user()
    team = await make_team(manager=manager)
    await make_member(member, team)
    task = await make_task(team, assignee=assignee)
    return SimpleNamespace(
        manager=manager,
        member=member,
        assignee=assignee,
        stranger=stranger,
        team=team,
        task=task,
    )