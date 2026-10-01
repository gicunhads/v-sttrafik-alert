import sqlite3
from datetime import datetime

from models import SavedTrip


DATABASE = "trip_alert.db"


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def create_tables():
    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS saved_trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            stop_id TEXT NOT NULL,
            stop_name TEXT NOT NULL,
            line TEXT NOT NULL,
            direction TEXT NOT NULL,
            target_time TEXT NOT NULL,
            days TEXT NOT NULL,
            delay_threshold INTEGER NOT NULL,
            FOREIGN KEY (user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS alerts_sent (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trip_id INTEGER NOT NULL,
            departure_time TEXT NOT NULL,
            reason TEXT NOT NULL,
            sent_at TEXT NOT NULL,

            FOREIGN KEY (trip_id)
                REFERENCES saved_trips(id)
                ON DELETE CASCADE,

            UNIQUE(
                trip_id,
                departure_time,
                reason
            )
        )
    """)
    connection.execute("""
    CREATE TABLE IF NOT EXISTS push_subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        endpoint TEXT NOT NULL UNIQUE,
        p256dh TEXT NOT NULL,
        auth TEXT NOT NULL,

        FOREIGN KEY (user_id)
            REFERENCES users(id)
            ON DELETE CASCADE
    )
""")

    connection.commit()
    connection.close()


def create_user(email, password_hash):
    connection = get_connection()

    cursor = connection.execute("""
        INSERT INTO users (
            email,
            password_hash
        )
        VALUES (?, ?)
    """, (
        email,
        password_hash
    ))

    connection.commit()

    user_id = cursor.lastrowid

    connection.close()

    return user_id


def get_user_by_email(email):
    connection = get_connection()

    user = connection.execute("""
        SELECT *
        FROM users
        WHERE email = ?
    """, (email,)).fetchone()

    connection.close()

    return user


def get_user_by_id(user_id):
    connection = get_connection()

    user = connection.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (user_id,)).fetchone()

    connection.close()

    return user


def insert_trip(trip):
    connection = get_connection()

    connection.execute("""
        INSERT INTO saved_trips (
            user_id,
            stop_id,
            stop_name,
            line,
            direction,
            target_time,
            days,
            delay_threshold
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        trip.user_id,
        trip.stop_id,
        trip.stop_name,
        trip.line,
        trip.direction,
        trip.target_time,
        ",".join(trip.days),
        trip.delay_threshold
    ))

    connection.commit()
    connection.close()


def row_to_trip(row):
    return SavedTrip(
        id=row["id"],
        user_id=row["user_id"],
        stop_id=row["stop_id"],
        stop_name=row["stop_name"],
        line=row["line"],
        direction=row["direction"],
        target_time=row["target_time"],
        days=row["days"].split(","),
        delay_threshold=row["delay_threshold"]
    )


def get_saved_trips(user_id=None):
    connection = get_connection()

    if user_id is None:
        rows = connection.execute("""
            SELECT *
            FROM saved_trips
            ORDER BY id DESC
        """).fetchall()

    else:
        rows = connection.execute("""
            SELECT *
            FROM saved_trips
            WHERE user_id = ?
            ORDER BY id DESC
        """, (user_id,)).fetchall()

    connection.close()

    return [
        row_to_trip(row)
        for row in rows
    ]


def delete_trip(trip_id, user_id):
    connection = get_connection()

    connection.execute("""
        DELETE FROM alerts_sent
        WHERE trip_id = ?
    """, (trip_id,))

    connection.execute("""
        DELETE FROM saved_trips
        WHERE id = ?
        AND user_id = ?
    """, (
        trip_id,
        user_id
    ))

    connection.commit()
    connection.close()


def alert_was_sent(
    trip_id,
    departure_time,
    reason
):
    connection = get_connection()

    row = connection.execute("""
        SELECT id
        FROM alerts_sent
        WHERE trip_id = ?
          AND departure_time = ?
          AND reason = ?
    """, (
        trip_id,
        departure_time,
        reason
    )).fetchone()

    connection.close()

    return row is not None


def record_alert(
    trip_id,
    departure_time,
    reason
):
    connection = get_connection()

    connection.execute("""
        INSERT OR IGNORE INTO alerts_sent (
            trip_id,
            departure_time,
            reason,
            sent_at
        )
        VALUES (?, ?, ?, ?)
    """, (
        trip_id,
        departure_time,
        reason,
        datetime.now().isoformat()
    ))

    connection.commit()
    connection.close()

def save_push_subscription(
    user_id,
    endpoint,
    p256dh,
    auth
):
    connection = get_connection()

    connection.execute("""
        INSERT INTO push_subscriptions (
            user_id,
            endpoint,
            p256dh,
            auth
        )
        VALUES (?, ?, ?, ?)

        ON CONFLICT(endpoint)
        DO UPDATE SET
            user_id = excluded.user_id,
            p256dh = excluded.p256dh,
            auth = excluded.auth
    """, (
        user_id,
        endpoint,
        p256dh,
        auth
    ))

    connection.commit()
    connection.close()


def get_push_subscriptions(user_id):
    connection = get_connection()

    rows = connection.execute("""
        SELECT *
        FROM push_subscriptions
        WHERE user_id = ?
    """, (user_id,)).fetchall()

    connection.close()

    return rows


def delete_push_subscription(endpoint):
    connection = get_connection()

    connection.execute("""
        DELETE FROM push_subscriptions
        WHERE endpoint = ?
    """, (endpoint,))

    connection.commit()
    connection.close()
