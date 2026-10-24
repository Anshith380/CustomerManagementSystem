
import pytest
import auth


class FakeCursor:
    def __init__(self, user=None):
        self.user = user
        self.query = ""
        self.params = ()

    def execute(self, query, params=()):
        self.query = query
        self.params = params

    def fetchone(self):
        return self.user

    def close(self):
        pass


class FakeConnection:
    def __init__(self, user=None):
        self.fake_cursor = FakeCursor(user)
        self.closed = False

    def cursor(self, dictionary=False):
        return self.fake_cursor

    def close(self):
        self.closed = True


def test_incorrect_password_is_rejected(monkeypatch):
    monkeypatch.setattr(
        auth,
        "get_connection",
        lambda: FakeConnection({
            "user_id": 1,
            "full_name": "Test Admin",
            "email": "admin@example.com",
            "password_hash": auth.hash_password("CorrectPassword123"),
            "role": "admin",
            "is_active": 1,
        }),
    )

    result = auth.authenticate_user(
        "admin@example.com", "WrongPassword123"
    )

    assert result is None


def test_inactive_account_cannot_log_in(monkeypatch):
    monkeypatch.setattr(
        auth,
        "get_connection",
        lambda: FakeConnection({
            "user_id": 2,
            "full_name": "Inactive User",
            "email": "inactive@example.com",
            "password_hash": auth.hash_password("CorrectPassword123"),
            "role": "employee",
            "is_active": 0,
        }),
    )

    result = auth.authenticate_user(
        "inactive@example.com", "CorrectPassword123"
    )

    assert result is None


def test_successful_login_does_not_return_password_hash(monkeypatch):
    monkeypatch.setattr(
        auth,
        "get_connection",
        lambda: FakeConnection({
            "user_id": 1,
            "full_name": "Test Admin",
            "email": "admin@example.com",
            "password_hash": auth.hash_password("CorrectPassword123"),
            "role": "admin",
            "is_active": 1,
        }),
    )

    result = auth.authenticate_user(
        " ADMIN@example.com ", "CorrectPassword123"
    )

    assert result is not None
    assert result["role"] == "admin"
    assert "password_hash" not in result


def test_logged_out_user_has_no_current_session(monkeypatch):
    monkeypatch.setattr(auth.st, "session_state", {})

    assert auth.current_user() is None


def test_invalid_role_cannot_log_in(monkeypatch):
    monkeypatch.setattr(
        auth,
        "get_connection",
        lambda: FakeConnection({
            "user_id": 4,
            "full_name": "Invalid Role User",
            "email": "invalid@example.com",
            "password_hash": auth.hash_password("CorrectPassword123"),
            "role": "superuser",
            "is_active": 1,
        }),
    )

    result = auth.authenticate_user(
        "invalid@example.com", "CorrectPassword123"
    )

    assert result is None
