
import lead_backend


class FakeCursor:
    """Simulates a database cursor for safe unit testing."""

    def __init__(self):
        self.query = ""
        self.params = ()
        self.rowcount = 0

    def execute(self, query, params=()):
        self.query = query
        self.params = params

    def fetchall(self):
        return [
            {
                "lead_id": 2,
                "assigned_to": 3,
                "assigned_name": "Anshith",
                "lead_status": "new",
            }
        ]

    def close(self):
        pass


class FakeConnection:
    """Simulates a database connection without changing real data."""

    def __init__(self):
        self.fake_cursor = FakeCursor()

    def cursor(self, dictionary=False):
        return self.fake_cursor

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


def test_employee_sees_only_assigned_leads(monkeypatch):
    connection = FakeConnection()

    monkeypatch.setattr(
        lead_backend,
        "current_user",
        lambda: {"user_id": 3, "role": "employee", "full_name": "Anshith"},
    )
    monkeypatch.setattr(
        lead_backend, "get_connection", lambda: connection
    )

    leads = lead_backend.get_leads()

    query = connection.fake_cursor.query.lower()
    params = connection.fake_cursor.params

    assert "l.assigned_to = %s" in query
    assert 3 in params
    assert all(lead["assigned_to"] == 3 for lead in leads)


def test_employee_update_is_limited_to_own_leads(monkeypatch):
    connection = FakeConnection()

    monkeypatch.setattr(
        lead_backend,
        "current_user",
        lambda: {"user_id": 3, "role": "employee", "full_name": "Anshith"},
    )
    monkeypatch.setattr(
        lead_backend, "get_connection", lambda: connection
    )

    lead_backend.update_lead_status(99, "contacted")

    query = connection.fake_cursor.query.lower()
    params = connection.fake_cursor.params

    assert "assigned_to = %s" in query
    assert params == ("contacted", 99, 3)


def test_invalid_lead_status_is_rejected(monkeypatch):
    monkeypatch.setattr(
        lead_backend,
        "current_user",
        lambda: {"user_id": 3, "role": "employee", "full_name": "Anshith"},
    )

    try:
        lead_backend.update_lead_status(2, "not_a_valid_status")
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid lead status was not rejected.")
