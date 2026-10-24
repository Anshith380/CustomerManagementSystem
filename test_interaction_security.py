
import interaction_backend


class FakeCursor:
    def __init__(self):
        self.query = ""
        self.params = ()
        self.rowcount = 0
        self.lastrowid = 101

    def execute(self, query, params=()):
        self.query = query
        self.params = params

    def fetchone(self):
        return {"customer_id": 10}

    def fetchall(self):
        return [{
            "interaction_id": 1,
            "customer_id": 10,
            "user_id": 3,
            "interaction_type": "call",
            "summary": "Customer follow-up",
        }]

    def close(self):
        pass


class FakeConnection:
    def __init__(self):
        self.fake_cursor = FakeCursor()
        self.committed = False
        self.rolled_back = False

    def cursor(self, dictionary=False):
        return self.fake_cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


def employee_user():
    return {
        "user_id": 3,
        "role": "employee",
        "full_name": "Anshith",
    }


def test_employee_sees_only_own_interactions(monkeypatch):
    connection = FakeConnection()

    monkeypatch.setattr(
        interaction_backend, "current_user", employee_user
    )
    monkeypatch.setattr(
        interaction_backend, "get_connection", lambda: connection
    )

    interactions = interaction_backend.get_interactions()

    query = connection.fake_cursor.query.lower()
    params = connection.fake_cursor.params

    assert "i.user_id = %s" in query
    assert 3 in params
    assert all(item["user_id"] == 3 for item in interactions)


def test_invalid_interaction_type_is_rejected(monkeypatch):
    monkeypatch.setattr(
        interaction_backend, "current_user", employee_user
    )

    try:
        interaction_backend.create_interaction(
            10, "invalid_type", "Test interaction"
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Invalid interaction type was not rejected."
        )


def test_empty_summary_is_rejected(monkeypatch):
    monkeypatch.setattr(
        interaction_backend, "current_user", employee_user
    )

    try:
        interaction_backend.create_interaction(
            10, "call", "   "
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Empty interaction summary was not rejected."
        )


def test_interaction_is_recorded_under_logged_in_user(monkeypatch):
    connection = FakeConnection()

    monkeypatch.setattr(
        interaction_backend, "current_user", employee_user
    )
    monkeypatch.setattr(
        interaction_backend, "get_connection", lambda: connection
    )

    interaction_id = interaction_backend.create_interaction(
        10, "call", "Customer follow-up", "Discussed requirements"
    )

    query = connection.fake_cursor.query.lower()

    assert "insert into interactions" in query
    assert 3 in connection.fake_cursor.params
    assert interaction_id == 101
    assert connection.committed is True
