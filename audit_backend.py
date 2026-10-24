
from database import get_connection
from auth import current_user


def log_action(
    action,
    entity_type,
    entity_id=None,
    details=None,
    user_id=None,
):
    """Record an audit action for the specified or logged-in user."""

    if user_id is None:
        user = current_user()
        if user:
            user_id = user["user_id"]

    if not action or not str(action).strip():
        raise ValueError("Action is required.")

    if not entity_type or not str(entity_type).strip():
        raise ValueError("Entity type is required.")

    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO audit_logs
                (user_id, action, entity_type, entity_id, details)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                user_id,
                str(action).strip()[:100],
                str(entity_type).strip()[:100],
                entity_id,
                str(details) if details is not None else None,
            ),
        )

        connection.commit()
        return cursor.lastrowid

    except Exception:
        connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        connection.close()


def get_audit_logs(limit=100):
    """Return recent audit records. Only admins may view audit logs."""

    from auth import enforce_role

    enforce_role("admin")

    limit = max(1, min(int(limit), 500))

    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                a.audit_id,
                a.user_id,
                u.full_name,
                a.action,
                a.entity_type,
                a.entity_id,
                a.details,
                a.created_at
            FROM audit_logs AS a
            LEFT JOIN users AS u
                ON u.user_id = a.user_id
            ORDER BY a.created_at DESC, a.audit_id DESC
            LIMIT %s
            """,
            (limit,),
        )

        return cursor.fetchall()

    finally:
        if cursor:
            cursor.close()
        connection.close()
