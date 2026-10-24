
import pytest
import backend


def employee_user():
    return {
        "user_id": 3,
        "full_name": "Anshith",
        "email": "employee.test@example.com",
        "role": "employee",
    }


@pytest.fixture(autouse=True)
def login_as_employee(monkeypatch):
    monkeypatch.setattr(backend, "current_user", employee_user)


def test_employee_cannot_add_customer():
    with pytest.raises(PermissionError):
        backend.add_customer(
            first_name="Test",
            last_name="Customer",
            email="employee.blocked@example.com",
        )


def test_employee_cannot_update_customer():
    with pytest.raises(PermissionError):
        backend.update_customer(
            customer_id=1,
            first_name="Updated",
            last_name="Customer",
        )


def test_employee_cannot_archive_customer():
    with pytest.raises(PermissionError):
        backend.archive_customer(customer_id=1)


def test_employee_can_view_customers(monkeypatch):
    class FakeCursor:
        def execute(self, query, params=()):
            self.query = query
            self.params = params

        def fetchall(self):
            return []

        def close(self):
            pass

    class FakeConnection:
        def __init__(self):
            self.fake_cursor = FakeCursor()

        def cursor(self, dictionary=False):
            return self.fake_cursor

        def close(self):
            pass

    connection = FakeConnection()
    monkeypatch.setattr(
        backend, "get_connection", lambda: connection
    )

    customers = backend.get_customers()

    assert customers == []
