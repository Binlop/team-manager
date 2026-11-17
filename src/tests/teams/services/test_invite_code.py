import string

from teams.services import TeamService, hash_invite_code

INVITE_CODE = "RawInvite01"


# --- hash_invite_code -------------------------------------------------------


def test_hash_invite_code_is_deterministic():
    assert hash_invite_code(INVITE_CODE) == hash_invite_code(INVITE_CODE)


def test_hash_invite_code_depends_on_input():
    assert hash_invite_code("one") != hash_invite_code("two")


def test_hash_invite_code_is_sha256_hex():
    digest = hash_invite_code(INVITE_CODE)

    assert len(digest) == 64
    assert all(char in string.hexdigits for char in digest)


# --- generate_invite_code ---------------------------------------------------


def test_generate_invite_code_default_length():
    code = TeamService.generate_invite_code()

    assert len(code) == 12
    assert all(char in string.ascii_letters + string.digits for char in code)


def test_generate_invite_code_custom_length():
    code = TeamService.generate_invite_code(length=32)

    assert len(code) == 32


def test_generate_invite_code_is_random():
    assert TeamService.generate_invite_code() != TeamService.generate_invite_code()
