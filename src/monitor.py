from datetime import datetime

from database import (
    get_saved_trips,
    alert_was_sent,
    record_alert
)
from trafiklab import get_departures
from departures import find_departure, should_notify
from push_notifications import (
    send_push_to_user
)


def should_check_now(trip, minutes_before=30):
    now = datetime.now()

    target = datetime.strptime(
        trip.target_time,
        "%H:%M"
    )

    current_minutes = (
        now.hour * 60
        + now.minute
    )

    target_minutes = (
        target.hour * 60
        + target.minute
    )

    minutes_until_trip = (
        target_minutes - current_minutes
    )

    return 0 <= minutes_until_trip <= minutes_before


def check_saved_trips():
    trips = get_saved_trips()
    today = datetime.now().strftime("%A")

    print(f"\nChecking {len(trips)} saved trip(s)...")

    for trip in trips:

        # Is this trip scheduled for today?
        if today not in trip.days:
            print(
                f"Skipping {trip.line} → {trip.direction}: "
                f"not scheduled for {today}"
            )
            continue

        # Is the trip happening within the next 30 minutes?
        if not should_check_now(trip):
            print(
                f"Skipping {trip.line} → {trip.direction}: "
                f"not within monitoring window"
            )
            continue

        print(
            f"Checking {trip.line} → {trip.direction} "
            f"from {trip.stop_name}"
        )

        # Only call Trafiklab when we actually need to check
        departures = get_departures(trip.stop_id)

        departure = find_departure(
            departures,
            trip
        )

        if departure is None:
            print("Departure not found.")
            continue

        reasons = should_notify(
            trip,
            departure
        )

        if not reasons:
            print("No notification needed.")
            continue

        # Create one string representing this alert
        reason_text = "\n".join(reasons)
        departure_time = departure["scheduled"]

        # Check SQLite instead of Python memory
        if alert_was_sent(
            trip.id,
            departure_time,
            reason_text
        ):
            print("Alert already sent.")
            continue

        send_push_to_user(
    user_id=trip.user_id,
    title=(
        f"Trip Alert: "
        f"{trip.line} → {trip.direction}"
    ),
    message=reason_text
)

        # Remember the notification in SQLite
        record_alert(
            trip.id,
            departure_time,
            reason_text
        )

        print("Notification sent.")


if __name__ == "__main__":
    check_saved_trips()
