from typing import List, Dict, Tuple
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials
from gspread import Spreadsheet

from .Event import Event
from storage import get_sheet_link


CREDS_PATH = "credentials.json"
GOOGLE_SHEET_READ_ONLY_SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

class Sheet:
    _instance = None

    def __init__(self):
        self.events: List[Event] = []
        self.people_data: List[Dict[str, int | float | str]] = []

    @classmethod
    def get_instance(cls) -> "Sheet":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def update_from_link(self):
        """Fetch the latest events and people data from the Google Sheet."""
        sheet_url = get_sheet_link()
        if not sheet_url:
            raise NoSheetLink("Please add a sheet link with /schedule link <google sheet link>")

        creds = Credentials.from_service_account_file(  # type: ignore
            CREDS_PATH, scopes=GOOGLE_SHEET_READ_ONLY_SCOPES)  # type: ignore
        gc = gspread.authorize(creds)
        all_data = gc.open_by_url(sheet_url)

        schedule_data, people_data = _data_from_sheets(all_data)

        self.people_data = people_data

        self.events = []
        for row in schedule_data:
            event = Event(row, self.people_data)
            self.events.append(event)

    def upcoming_events(self, count: int = 3) -> List[Event]:
        """Return the next 'count' upcoming events."""
        self.update_from_link()
        now = datetime.now()
        upcoming = [event for event in self.events if event.date() >= now]
        upcoming.sort(key=lambda e: e.date())
        return upcoming[:count]

    def formatted_upcoming_events(self, count: int = 3) -> str:
        """Return the next 'count' upcoming events in a pretty printing format"""
        upcoming_events_strings = [str(event) for event in self.upcoming_events(count)]
        if not upcoming_events_strings:
            return "No upcoming events"

        message = "Upcoming Events:\n\n" + "\n\n".join(upcoming_events_strings)
        return message

    
def _data_from_sheets(data: Spreadsheet) -> Tuple[List[Dict[str, int | float | str]], List[Dict[str, int | float | str]]]:
    schedule_data = []
    people_data = []

    for worksheet in data.worksheets():
        sheet_name = worksheet.title
        sheet_rows = worksheet.get_all_records()

        if sheet_name == "Schedule":
            schedule_data = sheet_rows
        elif sheet_name == "Names + Addresses":
            people_data = sheet_rows

    return schedule_data, people_data


class SheetException(Exception): pass
class NoSheetLink(SheetException): pass
