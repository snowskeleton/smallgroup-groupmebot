from datetime import datetime
from typing import List, Dict


class Event:
    def __init__(
            self,
            row: Dict[str, int | float | str],
            people_data: List[Dict[str, int | float | str]]
        ):
        self.date_str = str(row.get("Date", ""))
        self.leader = str(row.get("Leader", ""))
        self.location_name = str(row.get("Location", ""))
        self.event_time = str(row.get("Time", ""))
        self.dessert = str(row.get("Dessert", ""))
        self.notes = str(row.get("Notes", ""))

        name_to_address = {str(p.get("Names", "")).strip().lower(): str(p.get("Address", "")).strip()
                           for p in people_data if p.get("Names") and p.get("Address")}

        location_key = str(self.location_name).strip().lower() if self.location_name else ""
        self.location_display = name_to_address.get(location_key, self.location_name)

    def date(self) -> datetime:
        return datetime.strptime(self.date_str, "%m/%d/%Y")

    def __str__(self) -> str:
        message = f"{self.date().strftime('%a %b %d %Y')}\n"
        if self.event_time:
            message += f"Time: {self.event_time}\n"
        message += f"Leader: {self.leader}\nLocation: {self.location_display}"
        if self.dessert:
            message += f"\nDessert: {self.dessert}"
        if self.notes:
            message += f"\nNotes: {self.notes}"
        return message
