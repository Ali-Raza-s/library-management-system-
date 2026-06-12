from datetime import datetime

from database.mysql_connection import connect_database


def log_activity(user_id, action_type, action_description, ip_address=None, created_by_role=None):
    """Store an activity log entry in the MySQL activity_logs table."""
    db_connection = connect_database()
    if db_connection is None:
        return False

    try:
        cursor = db_connection.cursor()
        cursor.execute(
            """
            INSERT INTO activity_logs
            (user_id, action_type, action_description, action_time, ip_address, created_by_role)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                action_type,
                action_description,
                datetime.now(),
                ip_address,
                created_by_role,
            ),
        )
        db_connection.commit()
        cursor.close()
        db_connection.close()
        return True
    except Exception as error_message:
        print("Activity log error:", error_message)
        if db_connection is not None:
            db_connection.close()
        return False


def get_recent_logs(limit=50):
    """Fetch recent activity logs from MySQL for the admin report page."""
    db_connection = connect_database()
    if db_connection is None:
        return []

    try:
        cursor = db_connection.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
                al.log_id,
                al.user_id,
                COALESCE(u.name, 'System') AS user_name,
                al.action_type AS action,
                al.action_description AS details,
                al.action_time AS timestamp,
                al.ip_address,
                al.created_by_role
            FROM activity_logs al
            LEFT JOIN users u ON al.user_id = u.user_id
            ORDER BY al.action_time DESC, al.log_id DESC
            LIMIT %s
            """,
            (limit,),
        )
        logs = cursor.fetchall()
        cursor.close()
        db_connection.close()
        return logs
    except Exception as error_message:
        print("Get recent logs error:", error_message)
        if db_connection is not None:
            db_connection.close()
        return []
