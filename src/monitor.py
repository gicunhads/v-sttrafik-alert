from datetime import datetime
from zoneinfo import ZoneInfo

from database import (
    get_saved_trips,
    alert_was_sent,
    record_alert
)
from trafiklab import get_departures
from departures import (
    find_departure,
    should_notify
)
from push_notifications import (
    send_push_to_user
)


SWEDEN_TIMEZONE = ZoneInfo(
    "Europe/Stockholm"
)


def should_check_now(
    trip,
    minutes_before=30,
    minutes_after=30
):
    now = datetime.now(
        SWEDEN_TIMEZONE
    )

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
        target_minutes
        - current_minutes
    )

    return (
        -minutes_after
        <= minutes_until_trip
        <= minutes_before
    )


def check_saved_trips():
    trips = get_saved_trips()

    today = datetime.now(
        SWEDEN_TIMEZONE
    ).strftime("%A")

    print(
        f"\nChecking "
        f"{len(trips)} saved trip(s)..."
    )

    for trip in trips:

        # Only monitor trips scheduled
        # for the current weekday.
        if today not in trip.days:
            print(
                f"Skipping {trip.line} "
                f"→ {trip.direction}: "
                f"not scheduled for {today}"
            )
            continue

        # Monitor from 30 minutes before
        # until 30 minutes after the
        # scheduled departure.
        if not should_check_now(trip):
            print(
                f"Skipping {trip.line} "
                f"→ {trip.direction}: "
                f"not within monitoring window"
            )
            continue

        print(
            f"Checking {trip.line} "
            f"→ {trip.direction} "
            f"from {trip.stop_name}"
        )

        # Only call Trafiklab when this
        # trip actually needs checking.
        departures = get_departures(
            trip.stop_id
        )

        departure = find_departure(
            departures,
            trip
        )

        if departure is None:
            print(
                "Departure not found."
            )
            continue

        reasons = should_notify(
            trip,
            departure
        )

        if not reasons:
            print(
                "No notification needed."
            )
            continue

        reason_text = "\n".join(
            reasons
        )

        departure_time = departure[
            "scheduled"
        ]

        # Do not send the exact same
        # alert repeatedly.
        if alert_was_sent(
            trip.id,
            departure_time,
            reason_text
        ):
            print(
                "Alert already sent."
            )
            continue

        successful_pushes = (
            send_push_to_user(
                user_id=trip.user_id,
                title=(
                    f"Trip Alert: "
                    f"{trip.line} → "
                    f"{trip.direction}"
                ),
                message=reason_text
            )
        )

        # Only record the alert if at
        # least one device actually
        # received the push.
        if successful_pushes > 0:

            record_alert(
                trip.id,
                departure_time,
                reason_text
            )

            print(
                f"Notification sent to "
                f"{successful_pushes} "
                f"device(s)."
            )

        else:

            print(
                "Notification was not "
                "delivered. Alert was "
                "not marked as sent."
            )


if __name__ == "__main__":
    check_saved_trips()
