
from database import get_connection
from auth import hash_password, require_role


ALLOWED_ROLES = {"admin", "manager", "employee"}


def create_user(full_name, email, password, role):
    """Create a user account. Only admins can do this."""

    require_role("admin")

    full_name = (full_name or "").strip()
    email = (email or "").strip().lower()

    if not full_name or not email:
        raise ValueError("Name and email are required.")

    if role not in ALLOWED_ROLES:
        raise ValueError("Invalid user role.")

    password_hash = hash_password(password)

    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO users
                (full_name, email, password_hash, role, is_active)
            VALUES (%s, %s, %s, %s, TRUE)
            """,
            (full_name, email, password_hash, role),
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


def get_users():
    """Return user details without exposing password hashes."""

    require_role("admin")

    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT user_id, full_name, email, role,
                   is_active, created_at
            FROM users
            ORDER BY user_id DESC
            """
        )
        return cursor.fetchall()

    finally:
        if cursor:
            cursor.close()
        connection.close()


def set_user_active(user_id, is_active, actor_user_id):
    """Activate or deactivate an account."""

    require_role("admin")

    if int(user_id) == int(actor_user_id) and not is_active:
        raise ValueError("You cannot deactivate your own account.")

    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            UPDATE users
            SET is_active = %s
            WHERE user_id = %s
            """,
            (bool(is_active), user_id),
        )
        connection.commit()
        return cursor.rowcount

    except Exception:
        connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        connection.close()
