def get_status(departure):
    if departure["canceled"]:
        return "CANCELLED"

    if not departure["is_realtime"]:
        return "SCHEDULED"

    delay_minutes = round(departure["delay"] / 60)

    if delay_minutes > 0:
        return f"DELAYED {delay_minutes} min"

    return "ON TIME"


def print_departure(departure):
    route = departure["route"]

    transport = route["transport_mode"]
    line = route["designation"]
    direction = route["direction"]

    scheduled = departure["scheduled"][11:16]
    realtime = departure["realtime"][11:16]

    status = get_status(departure)

    print(
        f"{transport} {line} → {direction} | "
        f"{scheduled} → {realtime} | {status}"
    )

from datetime import datetime

from datetime import datetime


def find_departure(departures, saved_trip, tolerance_minutes=15):
    target = datetime.strptime(saved_trip.target_time, "%H:%M")

    matches = []

    for departure in departures:
        route = departure["route"]

        if route["designation"] != saved_trip.line:
            continue

        if saved_trip.direction.lower() not in route["direction"].lower():
            continue

        departure_time = datetime.fromisoformat(
            departure["scheduled"]
        )

        departure_minutes = (
            departure_time.hour * 60
            + departure_time.minute
        )

        target_minutes = (
            target.hour * 60
            + target.minute
        )

        difference = abs(departure_minutes - target_minutes)

        if difference <= tolerance_minutes:
            matches.append((difference, departure))

    if not matches:
        return None

    matches.sort(key=lambda match: match[0])

    return matches[0][1]

def should_notify(saved_trip, departure):
    reasons = []

    # Cancellation
    if departure["canceled"]:
        reasons.append("Trip has been cancelled")

    # Delay
    if departure["is_realtime"]:
        delay_minutes = departure["delay"] / 60

        if delay_minutes >= saved_trip.delay_threshold:
            reasons.append(
                f"Trip is delayed by {round(delay_minutes)} minutes"
            )

    # Platform change
    scheduled_platform = departure.get("scheduled_platform")
    realtime_platform = departure.get("realtime_platform")

    if scheduled_platform and realtime_platform:
        scheduled_designation = scheduled_platform.get("designation")
        realtime_designation = realtime_platform.get("designation")

        if scheduled_designation != realtime_designation:
            reasons.append(
                f"Platform changed from "
                f"{scheduled_designation} to {realtime_designation}"
            )

    # Service alerts
    if departure.get("alerts"):
        reasons.append("There is a service alert for this trip")

    return reasons
