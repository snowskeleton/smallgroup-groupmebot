from datetime import datetime, timedelta
from time import time
from typing import Dict, List

from google.oauth2.service_account import Credentials
from gspread import Spreadsheet, Worksheet, authorize
from gspread.utils import rowcol_to_a1

from .Event import Event
from .Person import Roster
from .Rotation import (Rotation, assign_rows, blank_rows, last_scheduled_date,
                       meeting_dates, parse_weekday)
from log import log
from storage import get_sheet_link



# Read/write: the bot appends generated rows to the Schedule tab. It never
# updates or deletes an existing row.
GOOGLE_SHEET_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

SCHEDULE_TAB = "Schedule"
PEOPLE_TAB = "People"
ROTATIONS_TAB = "Rotations"
CONFIG_TAB = "Config"
# Documentation for humans; not data.
IGNORED_TABS = {"README"}
RESERVED_TABS = {SCHEDULE_TAB, PEOPLE_TAB, ROTATIONS_TAB, CONFIG_TAB} | IGNORED_TABS

CACHE_SECONDS = 60


class Sheet:
    _instance = None

    def __init__(self):
        self.schedule_headers: List[str] = []
        self.schedule_rows: List[Dict[str, str]] = []
        self.schedule_row_numbers: List[int] = []
        self.events: List[Event] = []
        self.roster = Roster([])
        self.rotations: List[Rotation] = []
        self.config: Dict[str, str] = {}
        # Every non-reserved tab becomes an ordered list a rotation can draw
        # from, keyed by tab name.
        self.pools: Dict[str, List[str]] = {}
        self._fetched_at = 0.0

    @classmethod
    def get_instance(cls) -> "Sheet":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # --- Loading ---

    def _open(self) -> Spreadsheet:
        creds = Credentials.from_service_account_file(  # type: ignore
            CREDS_PATH, scopes=GOOGLE_SHEET_SCOPES)  # type: ignore
        return authorize(creds).open_by_url(get_sheet_link())

    def update_from_link(self, force: bool = False):
        """Fetch the sheet, unless we already did so very recently.

        A single command can ask for events and emails and upcoming dates; the
        cache keeps that to one round trip instead of three.
        """
        if not force and time() - self._fetched_at < CACHE_SECONDS:
            return
        self._load(self._open())
        self._fetched_at = time()

    def _load(self, spreadsheet: Spreadsheet):
        self.schedule_headers = []
        self.schedule_rows = []
        self.schedule_row_numbers = []
        self.pools = {}
        people_rows: List[Dict[str, str]] = []
        rotation_rows: List[Dict[str, str]] = []
        self.config = {}

        for worksheet in spreadsheet.worksheets():
            title = worksheet.title
            if title in IGNORED_TABS:
                continue

            headers, records, row_numbers = _records(worksheet)

            if title == SCHEDULE_TAB:
                self.schedule_headers = headers
                self.schedule_rows = records
                self.schedule_row_numbers = row_numbers
            elif title == PEOPLE_TAB:
                people_rows = records
            elif title == ROTATIONS_TAB:
                rotation_rows = records
            elif title == CONFIG_TAB:
                self.config = {str(r.get("Key", "")).strip(): str(r.get("Value", "")).strip()
                               for r in records if str(r.get("Key", "")).strip()}
            elif title not in RESERVED_TABS:
                self.pools[title] = _first_column(worksheet)

        self.roster = Roster(people_rows)
        self.rotations = [Rotation(r) for r in rotation_rows if str(r.get("Rotation", "")).strip()]

        self.events = []
        for row in self.schedule_rows:
            event = Event(row, self.roster, self.schedule_headers)
            if not event.date_str:
                continue
            try:
                event.date()
            except ValueError:
                log("ERROR", "sheet",
                    f"Skipping Schedule row with unreadable date {event.date_str!r} "
                    f"(expected MM/DD/YYYY)")
                continue
            if event.location_warning:
                log("WARN", "sheet", event.location_warning)
            self.events.append(event)

    # --- Reading ---

    def upcoming_events(self, count: int = 3) -> List[Event]:
        self.update_from_link()
        now = datetime.now()
        upcoming = [e for e in self.events if e.date() >= now]
        upcoming.sort(key=lambda e: e.date())
        return upcoming[:count]

    def formatted_upcoming_events(self, count: int = 3) -> str:
        strings = [str(event) for event in self.upcoming_events(count)]
        if not strings:
            return "No upcoming events"
        return "Upcoming Events:\n\n" + "\n\n".join(strings)

    def get_all_emails(self) -> List[str]:
        self.update_from_link()
        return self.roster.emails()

    def config_value(self, key: str, default: str) -> str:
        return self.config.get(key) or default

    # --- Writing ---

    def generate_schedule(self) -> str:
        """Lay down dates far out, then assign rotations only for the near term.

        Two horizons, because they answer different questions: `Weeks Ahead` is
        how far out you can pencil in "church retreat" or "I'm away", and
        `Assign Ahead` is how far out anyone is actually committed.

        Appends rows below the last one, and fills blank rotation cells. It
        never changes a cell that already has something in it.
        """
        spreadsheet = self._open()
        self._load(spreadsheet)
        self._fetched_at = time()

        if not self.schedule_headers:
            return "The Schedule tab has no headers — nothing to generate."
        if not self.rotations:
            return "The Rotations tab is empty — nothing to generate."

        worksheet = spreadsheet.worksheet(SCHEDULE_TAB)
        weekday = parse_weekday(self.config_value("Meeting Day", "Sunday"))
        default_time = self.config_value("Default Time", "")
        weeks_ahead = self._int_config("Weeks Ahead", 16)
        assign_ahead = self._int_config("Assign Ahead", 4)

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

        # --- Phase one: dates ---
        latest = last_scheduled_date(self.schedule_rows)
        start_after = max(latest, today) if latest else today
        dates = meeting_dates(start_after, today + timedelta(weeks=weeks_ahead), weekday)

        if dates:
            worksheet.append_rows(
                blank_rows(self.schedule_headers, dates, default_time),
                value_input_option="USER_ENTERED")
            # Re-read so the appended rows come back with real row numbers.
            self._load(spreadsheet)

        # --- Phase two: assignments ---
        updates = assign_rows(self.schedule_headers, self.schedule_rows,
                              self.rotations, self.roster, self.pools,
                              today, today + timedelta(weeks=assign_ahead))
        if updates:
            self._write_cells(worksheet, updates)

        self._fetched_at = 0.0

        parts = []
        if dates:
            parts.append(f"added {len(dates)} date(s) through "
                         f"{dates[-1].strftime('%b %d %Y')}")
        if updates:
            parts.append(f"filled {len(updates)} assignment(s) for the next "
                         f"{assign_ahead} week(s)")
        if not parts:
            return (f"Nothing to do — dates run {weeks_ahead} weeks out and the "
                    f"next {assign_ahead} weeks are assigned.")

        summary = "Schedule updated: " + ", ".join(parts) + "."
        log("INFO", "sheet", summary)
        return summary

    def _int_config(self, key: str, default: int) -> int:
        try:
            return int(self.config_value(key, str(default)))
        except ValueError:
            return default

    def _write_cells(self, worksheet: Worksheet, updates):
        """Write individual cells, addressed by their real position on the tab."""
        column_of = {h: i + 1 for i, h in enumerate(self.schedule_headers)}
        batch = []
        for record_index, header, value in updates:
            row = self.schedule_row_numbers[record_index]
            batch.append({"range": rowcol_to_a1(row, column_of[header]),
                          "values": [[value]]})
        worksheet.batch_update(batch, value_input_option="USER_ENTERED")


def _records(worksheet: Worksheet):
    """Header row, one dict per data row, and each row's number on the tab.

    Hand-rolled rather than get_all_records() so that blank trailing columns
    and duplicate headers degrade instead of raising.
    """
    values = worksheet.get_all_values()
    if not values:
        return [], [], []

    headers = [str(h).strip() for h in values[0]]
    records = []
    row_numbers = []
    for offset, row in enumerate(values[1:]):
        if not any(str(cell).strip() for cell in row):
            continue
        record = {}
        for index, header in enumerate(headers):
            if not header:
                continue
            record[header] = str(row[index]).strip() if index < len(row) else ""
        records.append(record)
        row_numbers.append(offset + 2)  # 1-indexed, past the header row
    return [h for h in headers if h], records, row_numbers


def _first_column(worksheet: Worksheet) -> List[str]:
    """Column A of a pool tab, header row dropped, blanks removed."""
    values = worksheet.col_values(1)
    return [str(v).strip() for v in values[1:] if str(v).strip()]
