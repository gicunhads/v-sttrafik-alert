from dataclasses import dataclass


@dataclass
class SavedTrip:
    stop_id: str
    stop_name: str
    line: str
    direction: str
    target_time: str
    days: list[str]
    delay_threshold: int = 5
    id: int | None = None
    user_id: int | None = None
