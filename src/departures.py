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
