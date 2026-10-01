import sqlite3

from models import SavedTrip


DATABASE = "trip_alert.db"


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def create_tables():
    connection = get_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS saved_trips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stop_id TEXT NOT NULL,
            stop_name TEXT NOT NULL,
            line TEXT NOT NULL,
            direction TEXT NOT NULL,
            target_time TEXT NOT NULL,
            days TEXT NOT NULL,
            delay_threshold INTEGER NOT NULL
        )
    """)
    connection.execute("""
    CREATE TABLE IF NOT EXISTS alerts_sent (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trip_id INTEGER NOT NULL,
        departure_time TEXT NOT NULL,
        reason TEXT NOT NULL,
        sent_at TEXT NOT NULL,
        UNIQUE(trip_id, departure_time, reason)
    )
""")
    connection.commit()
    connection.close()

from datetime import datetime


def alert_was_sent(trip_id, departure_time, reason):
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


def record_alert(trip_id, departure_time, reason):
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
def insert_trip(trip):
    connection = get_connection()

    connection.execute("""
        INSERT INTO saved_trips (
            stop_id,
            stop_name,
            line,
            direction,
            target_time,
            days,
            delay_threshold
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
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


def get_saved_trips():
    connection = get_connection()

    rows = connection.execute("""
        SELECT *
        FROM saved_trips
        ORDER BY id DESC
    """).fetchall()

    connection.close()

    trips = []

    for row in rows:
        trip = SavedTrip(
    id=row["id"],
    stop_id=row["stop_id"],
    stop_name=row["stop_name"],
    line=row["line"],
    direction=row["direction"],
    target_time=row["target_time"],
    days=row["days"].split(","),
    delay_threshold=row["delay_threshold"]
)

        trips.append(trip)
    
    return trips

def delete_trip(trip_id):
    connection = get_connection()

    connection.execute(
        "DELETE FROM saved_trips WHERE id = ?",
        (trip_id,)
    )

    connection.commit()
    connection.close()
