from datetime import datetime
from difflib import get_close_matches
from typing import Dict, List, Optional

DATE_FORMAT = "%m/%d/%Y"

# Columns the formatter handles specially; everything else on the Schedule tab
# is printed generically, so a new rotation column needs no code change here.
SPECIAL_COLUMNS = {"Date", "Time", "Location", "Notes"}


class Event:
    """One row of the Schedule tab."""

    def __init__(self, row: Dict[str, object], roster=None, headers: Optional[List[str]] = None):
        self.row = {str(k).strip(): str(v).strip() for k, v in row.items()}
        self.headers = headers or list(self.row.keys())

        self.date_str = self.row.get("Date", "")
        self.event_time = self.row.get("Time", "")
        self.location_name = self.row.get("Location", "")
        self.notes = self.row.get("Notes", "")
        # Kept for the GroupMe calendar-event title.
        self.leader = self.row.get("Leader", "")

        self.location_display = self.location_name
        self.location_warning = ""
        if roster is not None and self.location_name:
            self._resolve_location(roster)

    def _resolve_location(self, roster):
        """A household name becomes its street address. Anything else is a venue.

        An unmatched name that is *nearly* a household is almost always a typo
        rather than a real venue, so it gets flagged instead of silently
        printing as-is.
        """
        households = roster.households()
        lookup = {h.strip().lower(): h for h in households}
        key = self.location_name.strip().lower()

        if key in lookup:
            address = roster.address_for(lookup[key])
            self.location_display = address or self.location_name
            return

        near = get_close_matches(key, list(lookup.keys()), n=1, cutoff=0.8)
        if near:
            self.location_warning = (
                f"'{self.location_name}' didn't match a household — "
                f"did you mean '{lookup[near[0]]}'?")

    def date(self) -> datetime:
        return datetime.strptime(self.date_str, DATE_FORMAT)

    def __str__(self) -> str:
        message = f"{self.date().strftime('%a %b %d %Y')}\n"
        if self.event_time:
            message += f"Time: {self.event_time}\n"
        if self.location_display:
            message += f"Location: {self.location_display}\n"

        for header in self.headers:
            if header in SPECIAL_COLUMNS:
                continue
            value = self.row.get(header, "")
            if value:
                message += f"{header}: {value}\n"

        if self.notes:
            message += f"Notes: {self.notes}\n"

        return message.rstrip("\n")
