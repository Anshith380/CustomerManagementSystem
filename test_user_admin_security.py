
import pytest
import user_admin
import auth


def manager_user():
    return {
        "user_id": 2,
        "full_name": "Test Manager",
        "email": "manager@example.com",
        "role": "manager",
    }


def employee_user():
    return {
        "user_id": 3,
        "full_name": "Test Employee",
        "email": "employee@example.com",
        "role": "employee",
    }


@pytest.mark.parametrize(
    "user_factory",
    [manager_user, employee_user],
    ids=["manager", "employee"],
)
@pytest.mark.parametrize(
    "operation",
    ["create", "list", "deactivate"],
)
def test_non_admin_cannot_manage_users(
    monkeypatch, user_factory, operation
):
    # Simulate the selected logged-in user.
    monkeypatch.setattr(auth, "current_user", user_factory)

    # require_role is imported directly into user_admin.py,
    # so patch it there to verify the intended role restriction.
    def fake_require_role(*allowed_roles):
        user = user_factory()
        if user["role"] not in allowed_roles:
            raise PermissionError("Admin access required.")

    monkeypatch.setattr(
        user_admin, "require_role", fake_require_role
    )

    # These functions must reject non-admin users before DB access.
    with pytest.raises(PermissionError):
        if operation == "create":
            user_admin.create_user(
                "New Employee",
                "new.employee@example.com",
                "SecurePassword123",
                "employee",
            )
        elif operation == "list":
            user_admin.get_users()
        else:
            user_admin.set_user_active(
                user_id=4,
                is_active=False,
                actor_user_id=user_factory()["user_id"],
            )


def test_admin_role_is_required_for_user_management(monkeypatch):
    monkeypatch.setattr(
        user_admin,
        "require_role",
        lambda *roles: (
            None if roles == ("admin",)
            else (_ for _ in ()).throw(
                AssertionError("Unexpected role requirement")
            )
        ),
    )

    # The function should pass the admin guard and continue to DB access.
    class FakeCursor:
        rowcount = 1

        def execute(self, query, params=()):
            pass

        def close(self):
            pass

    class FakeConnection:
        def cursor(self, dictionary=False):
            return FakeCursor()

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(
        user_admin, "get_connection", lambda: FakeConnection()
    )

    result = user_admin.set_user_active(
        user_id=3,
        is_active=True,
        actor_user_id=1,
    )

    assert result == 1
