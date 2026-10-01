from datetime import datetime, timedelta
import os

from dotenv import load_dotenv

load_dotenv()
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    session,
    jsonify,
    send_from_directory
)
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)
from database import (
    create_tables,
    insert_trip,
    get_saved_trips,
    delete_trip,
    create_user,
    get_user_by_email,
    get_user_by_id
)
from functools import wraps
from trafiklab import search_stop, get_departures
from models import SavedTrip
from monitor import check_saved_trips

from database import (
    create_tables,
    insert_trip,
    get_saved_trips,
    delete_trip,
    save_push_subscription
)

from push_notifications import send_push_to_user

app = Flask(__name__)
app.secret_key = os.getenv(
    "FLASK_SECRET_KEY"
)

if not app.secret_key:
    raise ValueError(
        "FLASK_SECRET_KEY is missing from .env"
    )




def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):

        if "user_id" not in session:
            return redirect("/login")

        return view(*args, **kwargs)

    return wrapped_view


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
@login_required
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
@login_required
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
@login_required
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
    user_id=session["user_id"],
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
@login_required
def trips():

    saved_trips = get_saved_trips(
    session["user_id"]
)

    return render_template(
        "trips.html",
        trips=saved_trips
    )


@app.route(
    "/trip/<int:trip_id>/delete",
    methods=["POST"]
)
@login_required
def remove_trip(trip_id):

    delete_trip(
        trip_id,
        session["user_id"]
    )

    return redirect("/trips")




@app.route("/register", methods=["GET", "POST"])
def register():

    error = None

    if request.method == "POST":

        email = request.form["email"].strip().lower()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        if not email or not password or not confirm_password:
            error = "All fields are required."

        elif password != confirm_password:
            error = "Passwords do not match."

        elif len(password) < 8:
            error = "Password must be at least 8 characters."

        elif get_user_by_email(email):
            error = "An account with this email already exists."

        else:
            password_hash = generate_password_hash(
                password
            )

            user_id = create_user(
                email,
                password_hash
            )

            session["user_id"] = user_id

            return redirect("/")

    return render_template(
        "register.html",
        error=error
    )

@app.route("/login", methods=["GET", "POST"])
def login():

    error = None

    if request.method == "POST":

        email = request.form["email"].strip().lower()
        password = request.form["password"]

        user = get_user_by_email(email)

        if (
            user is None
            or not check_password_hash(
                user["password_hash"],
                password
            )
        ):
            error = "Incorrect email or password."

        else:
            session["user_id"] = user["id"]

            return redirect("/")

    return render_template(
        "login.html",
        error=error
    )

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/login")

@app.route(
    "/push/subscribe",
    methods=["POST"]
)
@login_required
def subscribe_push():

    subscription = request.get_json()

    if not subscription:
        return jsonify({
            "error": "Missing subscription"
        }), 400

    endpoint = subscription.get("endpoint")
    keys = subscription.get("keys", {})

    p256dh = keys.get("p256dh")
    auth = keys.get("auth")

    if not endpoint or not p256dh or not auth:
        return jsonify({
            "error": "Invalid subscription"
        }), 400

    save_push_subscription(
        user_id=session["user_id"],
        endpoint=endpoint,
        p256dh=p256dh,
        auth=auth
    )

    return jsonify({
        "success": True
    })

VAPID_PUBLIC_KEY = os.getenv(
    "VAPID_PUBLIC_KEY"
)

if not VAPID_PUBLIC_KEY:
    raise ValueError(
        "VAPID_PUBLIC_KEY is missing from .env"
    )

@app.route("/notifications")
@login_required
def notifications():

    return render_template(
        "notifications.html",
        vapid_public_key=VAPID_PUBLIC_KEY
    )

@app.route(
    "/push/test",
    methods=["POST"]
)
@login_required
def test_push():

    successful_pushes = send_push_to_user(
        user_id=session["user_id"],
        title="Trip Alert Test",
        message="Notifications are working!"
    )

    if successful_pushes == 0:
        return jsonify({
            "success": False,
            "error":
                "No notification was delivered."
        }), 500

    return jsonify({
        "success": True,
        "devices": successful_pushes
    })

@app.route("/service-worker.js")
def service_worker():
    return send_from_directory(
        "static",
        "service-worker.js",
        mimetype="application/javascript"
    )
@app.route("/manifest.json")
def manifest():
    return send_from_directory(
        "static",
        "manifest.json",
        mimetype="application/manifest+json"
    )




create_tables()
if __name__ == "__main__":

    app.run(
        debug=True,
        port=5001,
        use_reloader=False
    )
