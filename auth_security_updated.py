import bcrypt
import streamlit as st

from database import get_connection


VALID_ROLES = {"admin", "manager", "employee"}


def hash_password(password: str) -> str:
    """Hash a password with bcrypt before saving it."""
    if not isinstance(password, str) or len(password) < 10:
        raise ValueError("Password must contain at least 10 characters.")

    password_bytes = password.encode("utf-8")
    # bcrypt only processes the first 72 bytes.
    if len(password_bytes) > 72:
        raise ValueError("Password must be no more than 72 UTF-8 bytes.")

    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Safely check a password against its stored bcrypt hash."""
    if not isinstance(password, str) or not isinstance(password_hash, str):
        return False
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except (ValueError, TypeError, UnicodeError):
        return False


def authenticate_user(email: str, password: str):
    """Return a safe profile only when credentials and account are valid."""
    if not isinstance(email, str) or not isinstance(password, str):
        return None

    email = email.strip().lower()
    if not email or not password:
        return None

    connection = get_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT user_id, full_name, email, password_hash, role, is_active
            FROM users
            WHERE email = %s
            LIMIT 1
            """,
            (email,),
        )
        user = cursor.fetchone()

        if not user or not user["is_active"]:
            return None
        if user["role"] not in VALID_ROLES:
            return None
        if not verify_password(password, user["password_hash"]):
            return None

        # Never put the password hash in Streamlit session state.
        return {
            "user_id": user["user_id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "role": user["role"],
        }
    finally:
        if cursor:
            cursor.close()
        connection.close()


def current_user():
    """
    Refresh the session profile from MySQL.
    An inactive/deleted user or an unavailable database fails closed.
    """
    session_user = st.session_state.get("user")
    if not isinstance(session_user, dict) or not session_user.get("user_id"):
        return None

    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT user_id, full_name, email, role, is_active
            FROM users
            WHERE user_id = %s
            LIMIT 1
            """,
            (session_user["user_id"],),
        )
        user = cursor.fetchone()

        if not user or not user["is_active"] or user["role"] not in VALID_ROLES:
            st.session_state.pop("user", None)
            return None

        # Refresh role/name/email so changes in MySQL take effect.
        safe_user = {
            "user_id": user["user_id"],
            "full_name": user["full_name"],
            "email": user["email"],
            "role": user["role"],
        }
        st.session_state["user"] = safe_user
        return safe_user
    except Exception:
        # Fail closed rather than trusting a potentially stale session.
        st.session_state.pop("user", None)
        return None
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def has_role(*allowed_roles: str) -> bool:
    """Return True only when a valid current user has an allowed role."""
    if not allowed_roles or any(role not in VALID_ROLES for role in allowed_roles):
        return False
    user = current_user()
    return bool(user and user["role"] in allowed_roles)


def enforce_role(*allowed_roles: str):
    """
    Backend permission guard: raise an exception instead of stopping Streamlit.
    Use this in backend modules; keep require_role for UI page guards.
    """
    if not has_role(*allowed_roles):
        raise PermissionError("You do not have permission to perform this action.")


def require_role(*allowed_roles: str):
    """UI page guard: show an error and stop rendering an unauthorized page."""
    if not has_role(*allowed_roles):
        st.error("You do not have permission to access this feature.")
        st.stop()


def logout():
    """Clear the authenticated user's session."""
    st.session_state.pop("user", None)
    st.rerun()
