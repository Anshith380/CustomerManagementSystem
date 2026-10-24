
from database import get_connection
from auth import current_user
from audit_backend import log_action


# --------------------------------------------------
# CUSTOMER ACCESS CONTROL
# --------------------------------------------------

def _require_customer_view_access():
    """Allow authenticated users with recognized roles to view customers."""
    user = current_user()

    if not user:
        raise PermissionError("Please log in first.")

    if user.get("role") not in ("admin", "manager", "employee"):
        raise PermissionError("You cannot view customers.")

    return user


def _require_customer_manage_access():
    """Only Admin and Manager can manage customer records."""
    user = current_user()

    if not user:
        raise PermissionError("Please log in first.")

    if user.get("role") not in ("admin", "manager"):
        raise PermissionError(
            "Only Admin and Manager can add, edit, or archive customers."
        )

    return user


# --------------------------------------------------
# AUDIT LOGGING
# --------------------------------------------------

def _write_audit_log(action, customer_id, details, user_id):
    """Write an audit entry without undoing a successful customer operation."""
    try:
        log_action(
            action=action,
            entity_type="customer",
            entity_id=customer_id,
            details=details,
            user_id=user_id,
        )
    except Exception as exc:
        print(
            f"WARNING: Customer audit logging failed for "
            f"customer ID {customer_id}: {exc}"
        )


# --------------------------------------------------
# ADD CUSTOMER
# --------------------------------------------------

def add_customer(
    first_name,
    last_name,
    email=None,
    phone=None,
    company=None,
    address=None,
    source=None,
):
    """Create a customer and return the new customer ID."""

    user = _require_customer_manage_access()

    first_name = (first_name or "").strip()
    last_name = (last_name or "").strip()

    if not first_name or not last_name:
        raise ValueError("First name and last name are required.")

    email = email.strip().lower() if email and email.strip() else None
    phone = phone.strip() if phone and phone.strip() else None
    company = company.strip() if company and company.strip() else None
    address = address.strip() if address and address.strip() else None

    query = """
        INSERT INTO customers (
            first_name, last_name, email, phone,
            company, address, source
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """

    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor()

        cursor.execute(
            query,
            (
                first_name,
                last_name,
                email,
                phone,
                company,
                address,
                source,
            ),
        )

        customer_id = cursor.lastrowid
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
        customer_id=customer_id,
        details=(
            f"Customer created by {user['full_name']}: "
            f"{first_name} {last_name}"
        ),
        user_id=user["user_id"],
    )

    return customer_id


# --------------------------------------------------
# GET / SEARCH CUSTOMERS
# --------------------------------------------------

def get_customers(search="", status="all"):
    """Return customer records matching search and status filters."""

    _require_customer_view_access()

    allowed_statuses = {"all", "active", "inactive", "archived"}

    if status not in allowed_statuses:
        raise ValueError("Invalid customer status filter.")

    query = """
        SELECT
            customer_id,
            first_name,
            last_name,
            email,
            phone,
            company,
            address,
            status,
            source,
            created_at
        FROM customers
        WHERE (
            first_name LIKE %s
            OR last_name LIKE %s
            OR email LIKE %s
            OR company LIKE %s
        )
    """

    term = f"%{(search or '').strip()}%"
    params = [term, term, term, term]

    if status != "all":
        query += " AND status = %s"
        params.append(status)

    query += " ORDER BY created_at DESC"

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


# --------------------------------------------------
# UPDATE CUSTOMER
# --------------------------------------------------

def update_customer(
    customer_id,
    first_name,
    last_name,
    email=None,
    phone=None,
    company=None,
    address=None,
    source=None,
):
    """Update a customer's contact information."""

    user = _require_customer_manage_access()

    first_name = (first_name or "").strip()
    last_name = (last_name or "").strip()

    if not first_name or not last_name:
        raise ValueError("First name and last name are required.")

    email = email.strip().lower() if email and email.strip() else None
    phone = phone.strip() if phone and phone.strip() else None
    company = company.strip() if company and company.strip() else None
    address = address.strip() if address and address.strip() else None

    query = """
        UPDATE customers
        SET
            first_name = %s,
            last_name = %s,
            email = %s,
            phone = %s,
            company = %s,
            address = %s,
            source = %s
        WHERE customer_id = %s
          AND status != 'archived'
    """

    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor()

        cursor.execute(
            query,
            (
                first_name,
                last_name,
                email,
                phone,
                company,
                address,
                source,
                customer_id,
            ),
        )

        changed = cursor.rowcount
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        connection.close()

    if changed:
        _write_audit_log(
            action="UPDATE",
            customer_id=customer_id,
            details=(
                f"Customer updated by {user['full_name']}: "
                f"{first_name} {last_name}"
            ),
            user_id=user["user_id"],
        )

    return changed


# --------------------------------------------------
# ARCHIVE CUSTOMER
# --------------------------------------------------

def archive_customer(customer_id):
    """Archive a customer without deleting historical records."""

    user = _require_customer_manage_access()

    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE customers
            SET status = 'archived'
            WHERE customer_id = %s
              AND status != 'archived'
            """,
            (customer_id,),
        )

        archived = cursor.rowcount
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        connection.close()

    if archived:
        _write_audit_log(
            action="ARCHIVE",
            customer_id=customer_id,
            details=(
                f"Customer archived by {user['full_name']}"
            ),
            user_id=user["user_id"],
        )

    return archived
