from trafiklab import get_departures
from departures import find_departure, print_departure, should_notify
from notifications import send_notification
from models import SavedTrip

my_trip = SavedTrip(
    stop_id="740025617",
    stop_name="Chalmers",
    line="10",
    direction="Lindholmen",
    target_time="09:17",
    days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
    delay_threshold=5
)
departures = get_departures(my_trip.stop_id)

departure = find_departure(
    departures,
    my_trip
)

if departure:
    print("\nYOUR TRIP\n")
    print_departure(departure)


    reasons = should_notify(
        my_trip,
        departure
    )

    if reasons:
        print("\nALERT")

        for reason in reasons:
            print(f"- {reason}")

        message = "\n".join(reasons)

        send_notification(
            title=f"Trip Alert: {my_trip.line} → {my_trip.direction}",
            message=message
        )

    else:
        print("\nNo notification needed.")
else:
    print("Trip not found.")
