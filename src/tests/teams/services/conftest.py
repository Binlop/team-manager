from types import SimpleNamespace
from unittest.mock import create_autospec
 
import pytest
 
from auth.repositories import UserRepository
from teams.repositories import (
    MeetingRepository,
    TeamMemberRepository,
    TeamRepository,
)
 
 
def _mock_repo(cls):
    return create_autospec(cls, instance=True, spec_set=True)
 
 
@pytest.fixture
def team_repo():
    return _mock_repo(TeamRepository)
 
 
@pytest.fixture
def team_member_repo():
    return _mock_repo(TeamMemberRepository)
 
 
@pytest.fixture
def meeting_repo():
    return _mock_repo(MeetingRepository)
 
 
@pytest.fixture
def user_repo():
    return _mock_repo(UserRepository)
 
 
@pytest.fixture
def manager():
    """Текущий пользователь - менеджер команды."""
    return SimpleNamespace(id=1)
 
 
@pytest.fixture
def stranger():
    """Пользователь, не имеющий прав на команду/встречу."""
    return SimpleNamespace(id=2)
 
 
@pytest.fixture
def team(manager):
    return SimpleNamespace(id=10, manager_id=manager.id, invite_code="OlCODE")
