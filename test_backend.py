
from uuid import uuid4

import backend


def test_add_and_search_customer(monkeypatch):
    # Simulate an authorized Admin session in the backend.
    monkeypatch.setattr(
        backend,
        "current_user",
        lambda: {
            "user_id": 1,
            "full_name": "Test Admin",
            "email": "admin.test@example.com",
            "role": "admin",
        },
    )

    unique_email = f"rahul.{uuid4().hex}@example.com"

    customer_id = backend.add_customer(
        first_name="Rahul",
        last_name="Kumar",
        email=unique_email,
        phone="9876543210",
        company="ABC Technologies",
        address="Hyderabad",
        source="Website",
    )

    assert customer_id is not None

    customers = backend.get_customers(search=unique_email)

    assert any(
        customer["customer_id"] == customer_id
        and customer["email"] == unique_email
        for customer in customers
    )
