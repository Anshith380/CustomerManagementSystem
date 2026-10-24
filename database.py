
import os

import mysql.connector
import streamlit as st
from mysql.connector import Error


def get_connection():
    """Open a connection to the CRM MySQL database."""
    config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", ""),
        "password": os.getenv("DB_PASSWORD", "12345678"),
        "database": os.getenv("DB_NAME", "crm_db"),
    }

    if not config["user"] or not config["password"]:
        raise RuntimeError(
            "Set DB_USER and DB_PASSWORD in the environment first."
        )

    return mysql.connector.connect(**config)


def check_connection():
    """Return a simple connection status."""
    try:
        connection = get_connection()
        try:
            cursor = connection.cursor()
            cursor.execute("SELECT DATABASE()")
            result = cursor.fetchone()
            return True, result[0]
        finally:
            connection.close()
    except (Error, RuntimeError, ValueError):
        return False, None
