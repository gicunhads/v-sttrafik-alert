from trafiklab import get_departures
from departures import print_departure

CHALMERS_ID = "740025617"

departures = get_departures(CHALMERS_ID)

print("\nDEPARTURES FROM CHALMERS\n")

for departure in departures:
    print_departure(departure)
