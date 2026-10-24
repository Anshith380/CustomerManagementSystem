
import task_backend


class FakeCursor:
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
                "task_id": 1,
                "assigned_to": 3,
                "assigned_name": "Anshith",
                "title": "Follow up with customer",
                "status": "pending",
            }
        ]

    def close(self):
        pass


class FakeConnection:
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


def employee_user():
    return {
        "user_id": 3,
        "role": "employee",
        "full_name": "Anshith",
    }


def test_employee_sees_only_assigned_tasks(monkeypatch):
    connection = FakeConnection()

    monkeypatch.setattr(
        task_backend, "current_user", employee_user
    )
    monkeypatch.setattr(
        task_backend, "get_connection", lambda: connection
    )

    tasks = task_backend.get_tasks()

    query = connection.fake_cursor.query.lower()
    params = connection.fake_cursor.params

    assert "t.assigned_to = %s" in query
    assert 3 in params
    assert all(task["assigned_to"] == 3 for task in tasks)


def test_employee_update_is_limited_to_own_tasks(monkeypatch):
    connection = FakeConnection()

    monkeypatch.setattr(
        task_backend, "current_user", employee_user
    )
    monkeypatch.setattr(
        task_backend, "get_connection", lambda: connection
    )

    task_backend.update_task_status(99, "completed")

    query = connection.fake_cursor.query.lower()
    params = connection.fake_cursor.params

    assert "assigned_to = %s" in query
    assert params == ("completed", 99, 3)


def test_invalid_task_status_is_rejected(monkeypatch):
    monkeypatch.setattr(
        task_backend, "current_user", employee_user
    )

    try:
        task_backend.update_task_status(1, "invalid_status")
    except ValueError:
        pass
    else:
        raise AssertionError("Invalid task status was not rejected.")
