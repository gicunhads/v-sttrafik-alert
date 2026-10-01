import os
from datetime import datetime

from sqlalchemy import (
    create_engine,
    text,
)
from sqlalchemy.exc import IntegrityError

from models import SavedTrip


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///trip_alert.db"
)

# Some hosting providers historically return postgres://,
# while SQLAlchemy expects postgresql://.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace(
        "postgres://",
        "postgresql://",
        1
    )


engine_options = {
    "pool_pre_ping": True
}

# SQLite needs this when the Flask app and background
# scheduler access the database from different threads.
if DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {
        "check_same_thread": False
    }


engine = create_engine(
    DATABASE_URL,
    **engine_options
)


def create_tables():
    with engine.begin() as connection:

        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            )
        """))

        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS saved_trips (
                id INTEGER PRIMARY KEY,
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
        """))

        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS alerts_sent (
                id INTEGER PRIMARY KEY,
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
        """))

        connection.execute(text("""
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                endpoint TEXT NOT NULL UNIQUE,
                p256dh TEXT NOT NULL,
                auth TEXT NOT NULL,

                FOREIGN KEY (user_id)
                    REFERENCES users(id)
                    ON DELETE CASCADE
            )
        """))


def create_user(email, password_hash):
    with engine.begin() as connection:

        result = connection.execute(
            text("""
                INSERT INTO users (
                    email,
                    password_hash
                )
                VALUES (
                    :email,
                    :password_hash
                )
                RETURNING id
            """),
            {
                "email": email,
                "password_hash": password_hash
            }
        )

        return result.scalar_one()


def get_user_by_email(email):
    with engine.connect() as connection:

        row = connection.execute(
            text("""
                SELECT *
                FROM users
                WHERE email = :email
            """),
            {
                "email": email
            }
        ).mappings().first()

        return row


def get_user_by_id(user_id):
    with engine.connect() as connection:

        row = connection.execute(
            text("""
                SELECT *
                FROM users
                WHERE id = :user_id
            """),
            {
                "user_id": user_id
            }
        ).mappings().first()

        return row


def insert_trip(trip):
    with engine.begin() as connection:

        connection.execute(
            text("""
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
                VALUES (
                    :user_id,
                    :stop_id,
                    :stop_name,
                    :line,
                    :direction,
                    :target_time,
                    :days,
                    :delay_threshold
                )
            """),
            {
                "user_id": trip.user_id,
                "stop_id": trip.stop_id,
                "stop_name": trip.stop_name,
                "line": trip.line,
                "direction": trip.direction,
                "target_time": trip.target_time,
                "days": ",".join(trip.days),
                "delay_threshold":
                    trip.delay_threshold
            }
        )


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
    with engine.connect() as connection:

        if user_id is None:

            rows = connection.execute(
                text("""
                    SELECT *
                    FROM saved_trips
                    ORDER BY id DESC
                """)
            ).mappings().all()

        else:

            rows = connection.execute(
                text("""
                    SELECT *
                    FROM saved_trips
                    WHERE user_id = :user_id
                    ORDER BY id DESC
                """),
                {
                    "user_id": user_id
                }
            ).mappings().all()

        return [
            row_to_trip(row)
            for row in rows
        ]


def delete_trip(trip_id, user_id):
    with engine.begin() as connection:

        connection.execute(
            text("""
                DELETE FROM alerts_sent
                WHERE trip_id = :trip_id
            """),
            {
                "trip_id": trip_id
            }
        )

        connection.execute(
            text("""
                DELETE FROM saved_trips
                WHERE id = :trip_id
                AND user_id = :user_id
            """),
            {
                "trip_id": trip_id,
                "user_id": user_id
            }
        )


def alert_was_sent(
    trip_id,
    departure_time,
    reason
):
    with engine.connect() as connection:

        row = connection.execute(
            text("""
                SELECT id
                FROM alerts_sent
                WHERE trip_id = :trip_id
                  AND departure_time =
                      :departure_time
                  AND reason = :reason
            """),
            {
                "trip_id": trip_id,
                "departure_time":
                    departure_time,
                "reason": reason
            }
        ).first()

        return row is not None


def record_alert(
    trip_id,
    departure_time,
    reason
):
    try:
        with engine.begin() as connection:

            connection.execute(
                text("""
                    INSERT INTO alerts_sent (
                        trip_id,
                        departure_time,
                        reason,
                        sent_at
                    )
                    VALUES (
                        :trip_id,
                        :departure_time,
                        :reason,
                        :sent_at
                    )
                """),
                {
                    "trip_id": trip_id,
                    "departure_time":
                        departure_time,
                    "reason": reason,
                    "sent_at":
                        datetime.now().isoformat()
                }
            )

    except IntegrityError:
        # The UNIQUE constraint means the same
        # alert was already recorded.
        pass


def save_push_subscription(
    user_id,
    endpoint,
    p256dh,
    auth
):
    with engine.begin() as connection:

        connection.execute(
            text("""
                INSERT INTO push_subscriptions (
                    user_id,
                    endpoint,
                    p256dh,
                    auth
                )
                VALUES (
                    :user_id,
                    :endpoint,
                    :p256dh,
                    :auth
                )

                ON CONFLICT(endpoint)
                DO UPDATE SET
                    user_id = excluded.user_id,
                    p256dh = excluded.p256dh,
                    auth = excluded.auth
            """),
            {
                "user_id": user_id,
                "endpoint": endpoint,
                "p256dh": p256dh,
                "auth": auth
            }
        )


def get_push_subscriptions(user_id):
    with engine.connect() as connection:

        rows = connection.execute(
            text("""
                SELECT *
                FROM push_subscriptions
                WHERE user_id = :user_id
            """),
            {
                "user_id": user_id
            }
        ).mappings().all()

        return rows


def delete_push_subscription(endpoint):
    with engine.begin() as connection:

        connection.execute(
            text("""
                DELETE FROM push_subscriptions
                WHERE endpoint = :endpoint
            """),
            {
                "endpoint": endpoint
            }
        )
