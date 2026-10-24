
from database import get_connection

connection = get_connection()

try:
    cursor = connection.cursor()
    cursor.execute("SHOW TABLES")

    print("Connected to crm_db successfully!")
    print("Tables:")

    for row in cursor.fetchall():
        print("-", row[0])

    cursor.close()
finally:
    connection.close()
