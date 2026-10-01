import os

import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("TRAFIKLAB_API_KEY")
BASE_URL = "https://realtime-api.trafiklab.se/v1"

if not API_KEY:
    raise ValueError("TRAFIKLAB_API_KEY is missing from .env")


def search_stop(stop_name):
    url = f"{BASE_URL}/stops/name/{stop_name}"

    response = requests.get(
        url,
        params={"key": API_KEY},
        timeout=10
    )

    response.raise_for_status()

    return response.json()["stop_groups"]


def get_departures(stop_id):
    url = f"{BASE_URL}/departures/{stop_id}"

    response = requests.get(
        url,
        params={"key": API_KEY},
        timeout=10
    )

    response.raise_for_status()

    return response.json()["departures"]
