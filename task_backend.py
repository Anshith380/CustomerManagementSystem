
from datetime import datetime

from database import get_connection
from auth import current_user, require_role
from audit_backend import log_action


TASK_STATUSES = [
    "pending",
    "in_progress",
    "completed",
    "cancelled",
]


# --------------------------------------------------
# AUTHENTICATION
# --------------------------------------------------

def _logged_in_user():
    """Return the logged-in user or reject unauthenticated access."""
    user = current_user()

    if not user:
        raise PermissionError("Please log in first.")

    if user.get("role") not in ("admin", "manager", "employee"):
        raise PermissionError("You cannot access tasks.")

    return user


# --------------------------------------------------
# AUDIT LOGGING
# --------------------------------------------------

def _write_task_audit_log(action, task_id, details, user_id):
    """
    Record a task audit event.

    A logging failure does not undo a task operation that has
    already been committed.
    """
    try:
        log_action(
            action=action,
            entity_type="task",
            entity_id=task_id,
            details=details,
            user_id=user_id,
        )
    except Exception as exc:
        print(
            f"WARNING: Task audit logging failed for "
            f"task ID {task_id}: {exc}"
        )


# --------------------------------------------------
# GET TASK ASSIGNEES
# --------------------------------------------------

def get_task_assignees():
    """Get active users available for task assignment."""
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
# CREATE TASK
# --------------------------------------------------

def create_task(
    title,
    customer_id=None,
    description=None,
    due_at=None,
    assigned_to=None,
):
    """Create a task and assign it to an active user."""

    user = _logged_in_user()
    title = (title or "").strip()

    if not title:
        raise ValueError("Task title is required.")

    if isinstance(due_at, datetime) and due_at.tzinfo is not None:
        due_at = due_at.replace(tzinfo=None)

    if user["role"] == "employee":
        # Employees can assign tasks only to themselves.
        assigned_to = user["user_id"]

    elif user["role"] in ("admin", "manager"):
        require_role("admin", "manager")

        if assigned_to is None:
            assigned_to = user["user_id"]

    else:
        raise PermissionError("You cannot create tasks.")

    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)

        if customer_id is not None:
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
            SELECT user_id
            FROM users
            WHERE user_id = %s
              AND is_active = TRUE
            """,
            (assigned_to,),
        )

        if not cursor.fetchone():
            raise ValueError("Select an active user for assignment.")

        cursor.execute(
            """
            INSERT INTO tasks
                (customer_id, assigned_to, title, description, due_at, status)
            VALUES (%s, %s, %s, %s, %s, 'pending')
            """,
            (
                customer_id,
                assigned_to,
                title,
                (description or "").strip() or None,
                due_at,
            ),
        )

        task_id = cursor.lastrowid
        connection.commit()

    except Exception:
        connection.rollback()
        raise

    finally:
        if cursor:
            cursor.close()
        connection.close()

    # Write the audit record after the task has been committed.
    _write_task_audit_log(
        action="CREATE",
        task_id=task_id,
        details=(
            f"Task created by {user['full_name']}: "
            f"{title}; assigned to user ID {assigned_to}"
        ),
        user_id=user["user_id"],
    )

    return task_id


# --------------------------------------------------
# GET / SEARCH TASKS
# --------------------------------------------------

def get_tasks(search="", status="all", due_filter="all"):
    """List tasks, restricting employees to their own assigned tasks."""

    user = _logged_in_user()

    if status not in ["all"] + TASK_STATUSES:
        raise ValueError("Invalid task status.")

    if due_filter not in ("all", "overdue", "today", "upcoming"):
        raise ValueError("Invalid due-date filter.")

    query = """
        SELECT
            t.task_id,
            t.customer_id,
            c.first_name AS customer_first_name,
            c.last_name AS customer_last_name,
            t.assigned_to,
            u.full_name AS assigned_name,
            t.title,
            t.description,
            t.due_at,
            t.status
        FROM tasks AS t
        LEFT JOIN customers AS c
            ON c.customer_id = t.customer_id
        LEFT JOIN users AS u
            ON u.user_id = t.assigned_to
        WHERE (
            t.title LIKE %s
            OR COALESCE(t.description, '') LIKE %s
            OR CAST(t.task_id AS CHAR) LIKE %s
            OR COALESCE(c.first_name, '') LIKE %s
            OR COALESCE(c.last_name, '') LIKE %s
        )
    """

    term = f"%{(search or '').strip()}%"
    params = [term, term, term, term, term]

    if status != "all":
        query += " AND t.status = %s"
        params.append(status)

    if user["role"] == "employee":
        query += " AND t.assigned_to = %s"
        params.append(user["user_id"])

    elif user["role"] not in ("admin", "manager"):
        raise PermissionError("You cannot view tasks.")

    if due_filter == "overdue":
        query += """
            AND t.due_at < NOW()
            AND t.status NOT IN ('completed', 'cancelled')
        """

    elif due_filter == "today":
        query += " AND DATE(t.due_at) = CURDATE()"

    elif due_filter == "upcoming":
        query += """
            AND t.due_at > NOW()
            AND t.status NOT IN ('completed', 'cancelled')
        """

    query += """
        ORDER BY
            CASE WHEN t.due_at IS NULL THEN 1 ELSE 0 END,
            t.due_at ASC,
            t.task_id DESC
    """

    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(query, params)
        return cursor.fetchall()

    finally:
        if cursor:
            cursor.close()
        connection.close()


# --------------------------------------------------
# UPDATE TASK STATUS
# --------------------------------------------------

def update_task_status(task_id, new_status):
    """Update task status with role and assignment checks."""

    user = _logged_in_user()

    if new_status not in TASK_STATUSES:
        raise ValueError("Invalid task status.")

    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor()

        query = """
            UPDATE tasks
            SET status = %s
            WHERE task_id = %s
        """

        params = [new_status, task_id]

        if user["role"] == "employee":
            # Ownership is enforced directly in the UPDATE query.
            query += " AND assigned_to = %s"
            params.append(user["user_id"])

        elif user["role"] not in ("admin", "manager"):
            raise PermissionError("You cannot update tasks.")

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

    # Log only when the UPDATE matched and changed a row.
    if changed:
        _write_task_audit_log(
            action="UPDATE",
            task_id=task_id,
            details=(
                f"Task status set to {new_status} "
                f"by {user['full_name']}"
            ),
            user_id=user["user_id"],
        )

    return changed
