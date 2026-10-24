
from getpass import getpass

from auth import hash_password
from database import get_connection


def main():
    full_name = input("Administrator full name: ").strip()
    email = input("Administrator email: ").strip().lower()

    if not full_name or not email:
        print("Name and email are required.")
        return

    password = getpass("Create a password (10+ characters): ")
    confirm = getpass("Confirm password: ")

    if password != confirm:
        print("Passwords do not match.")
        return

    try:
        password_hash = hash_password(password)
    except ValueError as error:
        print(error)
        return

    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor()
        cursor.execute(
            """
            INSERT INTO users
                (full_name, email, password_hash, role, is_active)
            VALUES (%s, %s, %s, 'admin', TRUE)
            """,
            (full_name, email, password_hash)
        )
        connection.commit()
        print("Administrator created successfully.")

    except Exception as error:
        connection.rollback()
        print("Could not create administrator. Check whether the email "
              "already exists and whether the database is available.")
        print("Technical details:", error)

    finally:
        if cursor:
            cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
