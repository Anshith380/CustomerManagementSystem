
from datetime import datetime

from database import get_connection
from auth import current_user
from audit_backend import log_action


INTERACTION_TYPES = ["call", "email", "meeting", "note"]


# --------------------------------------------------
# AUTHENTICATION
# --------------------------------------------------

def _logged_in_user():
    """Return the logged-in user or reject unauthenticated access."""
    user = current_user()

    if not user:
        raise PermissionError("Please log in first.")

    if user.get("role") not in ("admin", "manager", "employee"):
        raise PermissionError("You cannot access interactions.")

    return user


# --------------------------------------------------
# AUDIT LOGGING
# --------------------------------------------------

def _write_interaction_audit_log(
    action,
    interaction_id,
    details,
    user_id,
):
    """Record an audit entry without undoing a saved interaction."""
    try:
        log_action(
            action=action,
            entity_type="interaction",
            entity_id=interaction_id,
            details=details,
            user_id=user_id,
        )
    except Exception as exc:
        print(
            "WARNING: Interaction audit logging failed for "
            f"interaction ID {interaction_id}: {exc}"
        )


# --------------------------------------------------
# CREATE INTERACTION
# --------------------------------------------------

def create_interaction(
    customer_id,
    interaction_type,
    summary,
    details="",
    interaction_at=None,
):
    """Record a call, email, meeting, or note for a customer."""

    user = _logged_in_user()

    if interaction_type not in INTERACTION_TYPES:
        raise ValueError("Choose a valid interaction type.")

    summary = (summary or "").strip()

    if not summary:
        raise ValueError("Interaction summary is required.")

    if interaction_at is None:
        interaction_at = datetime.now()

    elif (
        isinstance(interaction_at, datetime)
        and interaction_at.tzinfo is not None
    ):
        interaction_at = interaction_at.replace(tzinfo=None)

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
            raise ValueError(
                "Select a valid, non-archived customer."
            )

        cursor.execute(
            """
            INSERT INTO interactions
                (
                    customer_id,
                    user_id,
                    interaction_type,
                    summary,
                    details,
                    interaction_at
                )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                customer_id,
                user["user_id"],
                interaction_type,
                summary,
                (details or "").strip() or None,
                interaction_at,
            ),
        )

        interaction_id = cursor.lastrowid
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        connection.close()

    # Log after the interaction has been committed.
    _write_interaction_audit_log(
        action="CREATE",
        interaction_id=interaction_id,
        details=(
            f"Interaction created by {user['full_name']}: "
            f"{interaction_type}; {summary}"
        ),
        user_id=user["user_id"],
    )

    return interaction_id


# --------------------------------------------------
# GET INTERACTIONS
# --------------------------------------------------

def get_interactions(
    customer_id=None,
    interaction_type="all",
    search="",
):
    """Return interaction history; employees see only their own records."""

    user = _logged_in_user()

    if interaction_type not in ["all"] + INTERACTION_TYPES:
        raise ValueError("Invalid interaction type.")

    term = f"%{(search or '').strip()}%"

    query = """
        SELECT
            i.interaction_id,
            i.customer_id,
            CONCAT(c.first_name, ' ', c.last_name) AS customer_name,
            i.user_id,
            u.full_name AS recorded_by,
            i.interaction_type,
            i.summary,
            i.details,
            i.interaction_at
        FROM interactions AS i
        INNER JOIN customers AS c
            ON c.customer_id = i.customer_id
        LEFT JOIN users AS u
            ON u.user_id = i.user_id
        WHERE (
            i.summary LIKE %s
            OR COALESCE(i.details, '') LIKE %s
            OR CONCAT(c.first_name, ' ', c.last_name) LIKE %s
            OR CAST(i.interaction_id AS CHAR) LIKE %s
        )
    """

    params = [term, term, term, term]

    if customer_id is not None:
        query += " AND i.customer_id = %s"
        params.append(customer_id)

    if interaction_type != "all":
        query += " AND i.interaction_type = %s"
        params.append(interaction_type)

    if user["role"] == "employee":
        query += " AND i.user_id = %s"
        params.append(user["user_id"])

    elif user["role"] not in ("admin", "manager"):
        raise PermissionError(
            "You cannot view customer interactions."
        )

    query += """
        ORDER BY i.interaction_at DESC, i.interaction_id DESC
    """

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
