
from datetime import datetime
from decimal import Decimal, InvalidOperation

from database import get_connection
from auth import current_user, require_role
from audit_backend import log_action


# --------------------------------------------------
# OPPORTUNITY STAGES
# --------------------------------------------------

OPPORTUNITY_STAGES = [
    "qualification",
    "proposal",
    "negotiation",
    "won",
    "lost",
]


# --------------------------------------------------
# AUTHENTICATION
# --------------------------------------------------

def _logged_in_user():
    """Return the logged-in user."""
    user = current_user()

    if not user:
        raise PermissionError("Please log in first.")

    return user


# --------------------------------------------------
# AUDIT LOGGING
# --------------------------------------------------

def _write_opportunity_audit_log(
    action,
    opportunity_id,
    details,
    user_id,
):
    """
    Record opportunity actions in audit_logs.

    Logging failures are printed to the terminal and do not
    undo opportunity operations that have already committed.
    """
    try:
        log_action(
            action=action,
            entity_type="opportunity",
            entity_id=opportunity_id,
            details=details,
            user_id=user_id,
        )

    except Exception as exc:
        print(
            f"WARNING: Opportunity audit logging failed for "
            f"opportunity ID {opportunity_id}: {exc}"
        )


# --------------------------------------------------
# GET OPPORTUNITY ASSIGNEES
# --------------------------------------------------

def get_opportunity_assignees():
    """Return active users who can own opportunities."""

    require_role("admin", "manager")

    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT user_id, full_name, email, role
            FROM users
            WHERE is_active = TRUE
            ORDER BY full_name
        """)

        return cursor.fetchall()

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# CREATE OPPORTUNITY
# --------------------------------------------------

def create_opportunity(
    customer_id,
    title,
    amount,
    expected_close_date=None,
    assigned_to=None,
):
    """Create an opportunity linked to an existing customer."""

    user = _logged_in_user()

    title = (title or "").strip()

    if not title:
        raise ValueError("Opportunity title is required.")

    try:
        amount = Decimal(str(amount))

    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Enter a valid opportunity amount.")

    if not amount.is_finite() or amount < 0:
        raise ValueError(
            "Opportunity amount must be a finite, non-negative number."
        )

    # Employee can assign an opportunity only to themselves.
    if user["role"] == "employee":
        assigned_to = user["user_id"]

    elif user["role"] in ("admin", "manager"):
        require_role("admin", "manager")

        if assigned_to is None:
            assigned_to = user["user_id"]

    else:
        raise PermissionError("You cannot create opportunities.")

    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        # Validate customer.
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
            raise ValueError(
                "Select a valid, non-archived customer."
            )

        # Validate assigned user.
        cursor.execute(
            """
            SELECT user_id
            FROM users
            WHERE user_id = %s
              AND is_active = TRUE
            """,
            (assigned_to,),
        )

        if not cursor.fetchone():
            raise ValueError(
                "Select an active user as opportunity owner."
            )

        # Insert opportunity.
        cursor.execute(
            """
            INSERT INTO opportunities
                (
                    customer_id,
                    title,
                    amount,
                    stage,
                    expected_close_date,
                    assigned_to
                )
            VALUES (%s, %s, %s, 'qualification', %s, %s)
            """,
            (
                customer_id,
                title,
                amount,
                expected_close_date,
                assigned_to,
            ),
        )

        opportunity_id = cursor.lastrowid

        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        connection.close()

    # Record the action after successful commit.
    _write_opportunity_audit_log(
        action="CREATE",
        opportunity_id=opportunity_id,
        details=(
            f"Opportunity created by {user['full_name']}: "
            f"{title}; amount {amount}; "
            f"assigned to user ID {assigned_to}"
        ),
        user_id=user["user_id"],
    )

    return opportunity_id


# --------------------------------------------------
# GET / SEARCH OPPORTUNITIES
# --------------------------------------------------

def get_opportunities(
    search="",
    stage="all",
    customer_id=None,
):
    """List opportunities; employees see only their own opportunities."""

    user = _logged_in_user()

    if stage not in ["all"] + OPPORTUNITY_STAGES:
        raise ValueError("Invalid opportunity stage.")

    term = f"%{(search or '').strip()}%"

    query = """
        SELECT
            o.opportunity_id,
            o.customer_id,
            CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
            o.title,
            o.amount,
            o.stage,
            o.expected_close_date,
            o.assigned_to,
            u.full_name AS owner_name
        FROM opportunities AS o
        INNER JOIN customers AS c
            ON c.customer_id = o.customer_id
        LEFT JOIN users AS u
            ON u.user_id = o.assigned_to
        WHERE (
            o.title LIKE %s
            OR CONCAT(c.first_name, ' ', c.last_name) LIKE %s
            OR CAST(o.opportunity_id AS CHAR) LIKE %s
        )
    """

    params = [term, term, term]

    if stage != "all":
        query += " AND o.stage = %s"
        params.append(stage)

    if customer_id is not None:
        query += " AND o.customer_id = %s"
        params.append(customer_id)

    if user["role"] == "employee":
        query += " AND o.assigned_to = %s"
        params.append(user["user_id"])

    elif user["role"] not in ("admin", "manager"):
        raise PermissionError("You cannot view opportunities.")

    query += " ORDER BY o.opportunity_id DESC"

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
# UPDATE OPPORTUNITY STAGE
# --------------------------------------------------

def update_opportunity_stage(opportunity_id, new_stage):
    """Update opportunity stage with role and ownership checks."""

    user = _logged_in_user()

    if new_stage not in OPPORTUNITY_STAGES:
        raise ValueError("Invalid opportunity stage.")

    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor()

        query = """
            UPDATE opportunities
            SET stage = %s
            WHERE opportunity_id = %s
        """

        params = [new_stage, opportunity_id]

        # Employees can update only their own opportunities.
        if user["role"] == "employee":
            query += " AND assigned_to = %s"
            params.append(user["user_id"])

        elif user["role"] not in ("admin", "manager"):
            raise PermissionError(
                "You cannot update opportunities."
            )

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

    # Log only when a row was updated.
    if changed:
        _write_opportunity_audit_log(
            action="UPDATE",
            opportunity_id=opportunity_id,
            details=(
                f"Opportunity stage set to {new_stage} "
                f"by {user['full_name']}"
            ),
            user_id=user["user_id"],
        )

    return changed
