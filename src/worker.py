import time
from datetime import datetime
from zoneinfo import ZoneInfo

from database import create_tables
from monitor import check_saved_trips


SWEDEN_TIMEZONE = ZoneInfo(
    "Europe/Stockholm"
)

CHECK_INTERVAL_SECONDS = 300


def run_worker():
    create_tables()

    print(
        "Trip Alert worker started."
    )

    while True:
        try:
            now = datetime.now(
                SWEDEN_TIMEZONE
            )

            print(
                "\nWorker check:",
                now.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )
            )

            check_saved_trips()

        except Exception as error:
            # One failed Trafiklab request should
            # not permanently kill the worker.
            print(
                "Worker check failed:",
                error
            )

        time.sleep(
            CHECK_INTERVAL_SECONDS
        )


if __name__ == "__main__":
    run_worker()
