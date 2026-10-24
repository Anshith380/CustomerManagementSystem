
import bcrypt
import streamlit as st
from database import get_connection


def hash_password(password: str) -> str:
    """Hash a password with bcrypt before saving it."""
    if len(password) < 10:
        raise ValueError("Password must contain at least 10 characters.")

    password_bytes = password.encode("utf-8")

    # bcrypt processes at most 72 password bytes.
    if len(password_bytes) > 72:
        raise ValueError("Password must be no more than 72 UTF-8 bytes.")

    hashed = bcrypt.hashpw(
        password_bytes,
        bcrypt.gensalt(rounds=12)
    )
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Check a password against its stored bcrypt hash."""
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8")
        )
    except (ValueError, TypeError, UnicodeError):
        return False


def authenticate_user(email: str, password: str):
    """Return an active user's safe profile after successful login."""
    email = email.strip().lower()

    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT user_id, full_name, email, password_hash,
                   role, is_active
            FROM users
            WHERE email = %s
            LIMIT 1
            """,
            (email,)
        )
        user = cursor.fetchone()

        # Use a generic failure message in the interface.
        if not user or not user["is_active"]:
            return None

        if not verify_password(password, user["password_hash"]):
            return None

        # Never put the password hash into session state.
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
    """Get the user currently logged into this Streamlit session."""
    return st.session_state.get("user")


def has_role(*allowed_roles: str) -> bool:
    """Check the logged-in user's role."""
    user = current_user()
    return bool(user and user["role"] in allowed_roles)


def require_role(*allowed_roles: str):
    """Stop execution if the user lacks the required role."""
    if not has_role(*allowed_roles):
        st.error("You do not have permission to access this feature.")
        st.stop()


def logout():
    """Clear the authenticated user's session."""
    st.session_state.pop("user", None)
    st.rerun()
