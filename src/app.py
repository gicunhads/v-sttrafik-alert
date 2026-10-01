from datetime import datetime, timedelta

from flask import (
    Flask,
    render_template,
    request,
    redirect
)

from apscheduler.schedulers.background import BackgroundScheduler

from trafiklab import search_stop, get_departures
from models import SavedTrip
from monitor import check_saved_trips

from database import (
    create_tables,
    insert_trip,
    get_saved_trips,
    delete_trip
)


app = Flask(__name__)


def get_next_selected_date(days):
    """
    Find the next calendar date matching one of
    the weekdays selected by the user.
    """

    today = datetime.now().date()

    for offset in range(8):
        date = today + timedelta(days=offset)

        if date.strftime("%A") in days:
            return date

    return None


@app.route("/", methods=["GET", "POST"])
def index():
    stops = []
    search = ""

    if request.method == "POST":
        search = request.form.get(
            "stop_name",
            ""
        ).strip()

        if search:
            stops = search_stop(search)

    return render_template(
        "index.html",
        stops=stops,
        search=search
    )


@app.route("/stop/<stop_id>")
def select_stop(stop_id):
    departures = get_departures(stop_id)

    stop_name = "Selected stop"

    if departures:
        stop_name = departures[0]["stop"]["name"]

    lines = {}

    for departure in departures:
        route = departure["route"]

        line = route["designation"]
        direction = route["direction"]
        transport = route["transport_mode"]

        if line not in lines:
            lines[line] = {
                "transport": transport,
                "directions": set()
            }

        lines[line]["directions"].add(direction)

    return render_template(
        "stop.html",
        stop_id=stop_id,
        stop_name=stop_name,
        lines=lines
    )


@app.route("/trip/new")
def new_trip():
    stop_id = request.args.get("stop_id")
    stop_name = request.args.get("stop_name")
    line = request.args.get("line")
    direction = request.args.get("direction")

    return render_template(
        "new_trip.html",
        stop_id=stop_id,
        stop_name=stop_name,
        line=line,
        direction=direction,
        departures=None,
        selected_days=[],
        approximate_time=""
    )


@app.route(
    "/trip/find-departures",
    methods=["POST"]
)
def find_trip_departures():

    stop_id = request.form["stop_id"]
    stop_name = request.form["stop_name"]
    line = request.form["line"]
    direction = request.form["direction"]

    days = request.form.getlist("days")

    approximate_time = request.form[
        "approximate_time"
    ]

    delay_threshold = int(
        request.form["delay_threshold"]
    )

    if not days:
        return "Please select at least one day.", 400

    next_date = get_next_selected_date(days)

    if next_date is None:
        return "Could not find selected day.", 400

    approximate = datetime.strptime(
        approximate_time,
        "%H:%M"
    )

    # Trafiklab returns a 60-minute interval.
    # Start 30 minutes before the requested time.
    search_datetime = datetime.combine(
        next_date,
        approximate.time()
    ) - timedelta(minutes=30)

    search_time = search_datetime.strftime(
        "%Y-%m-%dT%H:%M"
    )

    departures = get_departures(
        stop_id,
        search_time
    )

    matching_departures = []

    for departure in departures:
        route = departure["route"]

        if (
            route["designation"] == line
            and route["direction"] == direction
        ):
            scheduled = datetime.fromisoformat(
                departure["scheduled"]
            )

            requested = datetime.combine(
                next_date,
                approximate.time()
            )

            difference = abs(
                (
                    scheduled.replace(tzinfo=None)
                    - requested
                ).total_seconds()
            )

            matching_departures.append(
                (
                    difference,
                    departure
                )
            )

    matching_departures.sort(
        key=lambda item: item[0]
    )

    # Show at most the three closest departures
    closest_departures = [
        departure
        for _, departure
        in matching_departures[:3]
    ]

    return render_template(
        "new_trip.html",
        stop_id=stop_id,
        stop_name=stop_name,
        line=line,
        direction=direction,
        departures=closest_departures,
        selected_days=days,
        approximate_time=approximate_time,
        delay_threshold=delay_threshold,
        searched_date=next_date
    )


@app.route("/trip/save", methods=["POST"])
def save_trip():

    stop_id = request.form["stop_id"]
    stop_name = request.form["stop_name"]
    line = request.form["line"]
    direction = request.form["direction"]

    target_time = request.form["target_time"]

    days = request.form.getlist("days")

    delay_threshold = int(
        request.form["delay_threshold"]
    )

    saved_trip = SavedTrip(
        stop_id=stop_id,
        stop_name=stop_name,
        line=line,
        direction=direction,
        target_time=target_time,
        days=days,
        delay_threshold=delay_threshold
    )

    insert_trip(saved_trip)

    print("\nNEW SAVED TRIP")
    print(saved_trip)

    return render_template(
        "trip_saved.html",
        trip=saved_trip
    )


@app.route("/trips")
def trips():

    saved_trips = get_saved_trips()

    return render_template(
        "trips.html",
        trips=saved_trips
    )


@app.route(
    "/trip/<int:trip_id>/delete",
    methods=["POST"]
)
def remove_trip(trip_id):

    delete_trip(trip_id)

    return redirect("/trips")


create_tables()


if __name__ == "__main__":

    scheduler = BackgroundScheduler()

    scheduler.add_job(
        check_saved_trips,
        "interval",
        minutes=5
    )

    scheduler.start()

    app.run(
        debug=True,
        port=5001,
        use_reloader=False
    )
