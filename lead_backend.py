
from decimal import Decimal, InvalidOperation

from database import get_connection
from auth import current_user, require_role
from audit_backend import log_action


LEAD_STATUSES = [
    "new",
    "contacted",
    "qualified",
    "proposal",
    "converted",
    "lost",
]


def _get_user():
    user = current_user()
    if not user:
        raise PermissionError("Please log in first.")
    return user


def _write_audit_log(action, lead_id, details):
    """Record an audit event without undoing a successful lead operation."""
    try:
        log_action(
            action=action,
            entity_type="lead",
            entity_id=lead_id,
            details=details,
        )
    except Exception as exc:
        # The lead operation has already committed. Report audit failures
        # rather than pretending the audit entry was written.
        print(
            f"WARNING: Audit logging failed for lead {lead_id}: {exc}"
        )


def get_assignable_users():
    """Return active users who can be assigned leads."""
    require_role("admin", "manager")

    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT user_id, full_name, email, role
            FROM users
            WHERE is_active = TRUE
            ORDER BY full_name
            """
        )
        return cursor.fetchall()
    finally:
        if cursor:
            cursor.close()
        connection.close()


def create_lead(
    customer_id,
    estimated_value=0,
    expected_close_date=None,
    assigned_to=None,
):
    """Create a lead and record its creation in the audit log."""
    user = _get_user()
    role = user["role"]

    try:
        value = Decimal(str(estimated_value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Enter a valid estimated value.")

    if not value.is_finite() or value < 0:
        raise ValueError("Estimated value cannot be negative.")

    if role == "employee":
        assigned_to = user["user_id"]
    else:
        require_role("admin", "manager")
        if assigned_to is None:
            assigned_to = user["user_id"]

    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT customer_id
            FROM customers
            WHERE customer_id = %s
              AND status != 'archived'
            """,
            (customer_id,),
        )
        if not cursor.fetchone():
            raise ValueError("Select a valid, non-archived customer.")

        cursor.execute(
            """
            SELECT user_id
            FROM users
            WHERE user_id = %s AND is_active = TRUE
            """,
            (assigned_to,),
        )
        if not cursor.fetchone():
            raise ValueError("Select an active user for assignment.")

        cursor.execute(
            """
            INSERT INTO leads (
                customer_id,
                lead_status,
                estimated_value,
                expected_close_date,
                assigned_to
            )
            VALUES (%s, 'new', %s, %s, %s)
            """,
            (
                customer_id,
                value,
                expected_close_date,
                assigned_to,
            ),
        )

        lead_id = cursor.lastrowid
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        connection.close()

    _write_audit_log(
        action="CREATE",
        lead_id=lead_id,
        details=(
            f"Lead created by {user['full_name']}; "
            f"customer ID: {customer_id}; "
            f"assigned to user ID: {assigned_to}"
        ),
    )

    return lead_id


def get_leads(search="", status="all"):
    """Retrieve leads with customer information and role filtering."""
    user = _get_user()

    if status not in ["all"] + LEAD_STATUSES:
        raise ValueError("Invalid lead status.")

    query = """
        SELECT
            l.lead_id,
            l.customer_id,
            c.first_name,
            c.last_name,
            c.email AS customer_email,
            l.lead_status,
            l.estimated_value,
            l.expected_close_date,
            l.assigned_to,
            u.full_name AS assigned_name
        FROM leads AS l
        JOIN customers AS c
            ON c.customer_id = l.customer_id
        LEFT JOIN users AS u
            ON u.user_id = l.assigned_to
        WHERE (
            c.first_name LIKE %s
            OR c.last_name LIKE %s
            OR c.email LIKE %s
            OR CAST(l.lead_id AS CHAR) LIKE %s
        )
    """

    term = f"%{(search or '').strip()}%"
    params = [term, term, term, term]

    if status != "all":
        query += " AND l.lead_status = %s"
        params.append(status)

    if user["role"] == "employee":
        query += " AND l.assigned_to = %s"
        params.append(user["user_id"])
    elif user["role"] not in ("admin", "manager"):
        raise PermissionError("You do not have permission to view leads.")

    query += " ORDER BY l.lead_id DESC"

    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, tuple(params))
        return cursor.fetchall()
    finally:
        if cursor:
            cursor.close()
        connection.close()


def update_lead_status(lead_id, new_status):
    """Update lead status with ownership checks and audit logging."""
    user = _get_user()

    if new_status not in LEAD_STATUSES:
        raise ValueError("Invalid lead status.")

    if user["role"] not in ("admin", "manager", "employee"):
        raise PermissionError(
            "You do not have permission to update leads."
        )

    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor()

        # Keep the ownership restriction in the UPDATE itself.
        query = """
            UPDATE leads
            SET lead_status = %s
            WHERE lead_id = %s
        """
        params = [new_status, lead_id]

        if user["role"] == "employee":
            query += " AND assigned_to = %s"
            params.append(user["user_id"])

        cursor.execute(query, tuple(params))
        changed = cursor.rowcount
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        connection.close()

    # Do not issue a second SELECT just to create an audit record.
    # This keeps compatibility with existing test cursors and preserves
    # the atomic ownership condition in the UPDATE statement.
    if changed:
        _write_audit_log(
            action="UPDATE",
            lead_id=lead_id,
            details=(
                f"Lead status set to {new_status} "
                f"by {user['full_name']}"
            ),
        )

    return changed
