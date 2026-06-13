# ============================================================
# Smart-Shelf: Digital Library Manager
# File: mysql_connection.py
# Purpose: Connect Python (Flask) to MariaDB/MySQL database
# ============================================================

# Import mysql.connector library to talk to MySQL/MariaDB from Python
import mysql.connector
from mysql.connector import Error


# --- Database settings 
DB_HOST = "b755pswtvdsqosjgej88-mysql.services.clever-cloud.com"
DB_PORT = 3306
DB_NAME = "b755pswtvdsqosjgej88"
DB_USER = "uijh7a6d0b2t59jp"
DB_PASSWORD = "JKf23IzUKkA80XaRauIN"

def connect_database():
    """
    Create and return a connection to the smart_shelf database.
    Returns None if connection fails (so Flask can show an error message).
    """
    connection = None  # Start with no connection (safe default)

    try:
        # Try to open a connection using our settings above
        connection = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )

        # If we reach here, connection object was created successfully
        if connection.is_connected():
            print("Connected to MySQL database: smart_shelf")

    except Error as error_message:
        # If anything goes wrong (wrong password, server off, wrong DB name), show it
        print("Error while connecting to MySQL:", error_message)
        connection = None  # Make sure we do not return a broken connection

    # Return the connection to whoever called this function (e.g. Flask route)
    return connection


def ensure_users_created_at_column():
    """
    RBAC / User Management: safely add created_at to users table if missing.
    Does not delete or modify existing rows — only adds the column when needed.
    """
    db_connection = connect_database()
    if db_connection is None:
        return

    try:
        cursor = db_connection.cursor()
        cursor.execute("SHOW COLUMNS FROM users LIKE 'created_at'")
        column_exists = cursor.fetchone()

        if column_exists is None:
            cursor.execute(
                "ALTER TABLE users "
                "ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP"
            )
            db_connection.commit()
            print("Added created_at column to users table.")

        cursor.close()
        db_connection.close()
    except Error as error_message:
        print("Schema update error (created_at):", error_message)


def ensure_schema_tables():
    """Create or update the MySQL tables used by Smart-Shelf."""
    db_connection = connect_database()
    if db_connection is None:
        return

    try:
        cursor = db_connection.cursor()

        cursor.execute("SHOW COLUMNS FROM users LIKE 'cnic'")
        if cursor.fetchone() is None:
            cursor.execute("ALTER TABLE users ADD COLUMN cnic VARCHAR(20) UNIQUE")

        cursor.execute("SHOW COLUMNS FROM users LIKE 'phone_number'")
        if cursor.fetchone() is None:
            cursor.execute("ALTER TABLE users ADD COLUMN phone_number VARCHAR(20) UNIQUE")

        cursor.execute("SHOW COLUMNS FROM users LIKE 'address'")
        if cursor.fetchone() is None:
            cursor.execute("ALTER TABLE users ADD COLUMN address TEXT")

        cursor.execute("SHOW COLUMNS FROM books LIKE 'description'")
        if cursor.fetchone() is None:
            cursor.execute("ALTER TABLE books ADD COLUMN description TEXT")

        cursor.execute("SHOW COLUMNS FROM books LIKE 'publication_year'")
        if cursor.fetchone() is None:
            cursor.execute("ALTER TABLE books ADD COLUMN publication_year INT")

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_logs (
                log_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                action_type VARCHAR(100),
                action_description TEXT,
                action_time DATETIME DEFAULT CURRENT_TIMESTAMP,
                ip_address VARCHAR(45),
                created_by_role VARCHAR(50),
                CONSTRAINT fk_activity_logs_user
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS book_reviews (
                review_id INT AUTO_INCREMENT PRIMARY KEY,
                book_id INT,
                user_id INT,
                rating INT,
                review_text TEXT,
                review_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT fk_book_reviews_book
                    FOREIGN KEY (book_id) REFERENCES books(book_id),
                CONSTRAINT fk_book_reviews_user
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
            """
        )
        db_connection.commit()
        cursor.close()
        db_connection.close()
    except Error as error_message:
        print("Schema update error:", error_message)


# ============================================================
# Test section: run this file directly to check the connection
# Command: python database/mysql_connection.py
# ============================================================
if __name__ == "__main__":
    # Call our function once to test
    test_connection = connect_database()

    if test_connection is not None:
        # Get a cursor to run a simple SQL command (proves DB is really working)
        cursor = test_connection.cursor()
        cursor.execute("SELECT DATABASE();")
        row = cursor.fetchone()
        print("Current database:", row[0])

        # Close cursor and connection (good practice)
        cursor.close()
        test_connection.close()
        print("Connection closed.")
    else:
        print("Connection test failed. Check MySQL is running and settings are correct.")
