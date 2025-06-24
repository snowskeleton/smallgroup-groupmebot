from croniter import croniter
from datetime import datetime, timedelta
from pytz import timezone

import gspread
from google.oauth2.service_account import Credentials
import requests
import time

import commands
import difflib

from bot_secrets import BOT_NAME, BOT_ID
from storage import get_sheet_link, get_schedule


def check_secrets():
    """Ensure all uppercase variables in bot_secrets are non-empty."""
    import bot_secrets
    for key in dir(bot_secrets):
        if key.isupper():
            value = getattr(bot_secrets, key)
            if not value:
                raise ValueError(f"Missing or empty secret: {key}")


def to_or_from_the_bot(sender: str, text: str):
    if not text:
        return False
    if sender == BOT_NAME:
        return True
    if text.startswith("/"):
        return True
    return False


def send_message(text: str):
    url = "https://api.groupme.com/v3/bots/post"
    data = {"bot_id": BOT_ID, "text": text}
    requests.post(url, json=data)


def format_upcoming_events(sheet_url: str, creds_path: str, count: int) -> str:
    """Returns a formatted message listing the next 'count' upcoming events."""
    all_data = get_sheet_data(sheet_url, creds_path)

    schedule_data = []
    people_data = []

    for title, rows in all_data:
        if "Schedule" in title:
            schedule_data = rows
        elif "Names + Addresses" in title:
            people_data = rows

    if not schedule_data or not people_data:
        return "Error: Could not find required sheets."

    name_to_address = {}
    for row in people_data[1:]:
        name = row[0]
        address = row[3] if len(row) > 3 else ""
        if name and address:
            name_to_address[name.strip().lower()] = address.strip()

    now = datetime.now()
    upcoming = []
    for row in schedule_data[1:]:
        try:
            event_date = datetime.strptime(row[0], "%m/%d/%Y")
            if event_date >= now:
                upcoming.append(row)
        except Exception:
            continue

    upcoming.sort(key=lambda x: datetime.strptime(x[0], "%m/%d/%Y"))
    upcoming = upcoming[:count]

    message = "Upcoming Events:\n\n"
    for row in upcoming:
        date, leader, location_name, dessert, notes = (row + [""] * 5)[:5]

        location_key = location_name.strip().lower() if location_name else ""
        location_display = name_to_address.get(location_key, location_name)

        message += f"{datetime.strptime(date, '%m/%d/%Y').strftime('%a %b %d %Y')}\n"
        message += f"Leader: {leader}\nLocation: {location_display}"
        if dessert:
            message += f"\nDessert: {dessert}"
        if notes:
            message += f"\nNotes: {notes}"
        message += "\n\n"

    return message


def periodic_messages():
    local_tz = timezone("America/New_York")

    while True:
        schedule = get_schedule()
        if schedule:
            now = datetime.now(local_tz)

            # Truncate seconds for a clean comparison
            base = now.replace(second=0, microsecond=0)

            if croniter.match(schedule, base):
                send_message(commands.schedule_show("3"))
            else:
                print("better luck next time")
        time.sleep(60)


def process_message(sender: str, text: str) -> str | None:
    """Process incoming message and return a response string if applicable."""

    if not text.startswith("/"):
        return

    parts = text.strip().split(maxsplit=1)
    command = parts[0][1:].lower()  # Strip leading "/"
    args = parts[1] if len(parts) > 1 else ""

    if hasattr(commands, command):
        func = getattr(commands, command)
        if callable(func):
            return func(sender, args)  # type: ignore

    # Suggest similar commands
    available = [name for name in dir(commands) if callable(getattr(commands, name)) and not name.startswith("__")]
    suggestions = difflib.get_close_matches(command, available, n=1, cutoff=0.6)

    if suggestions:
        return f"Unknown command '/{command}'. Did you mean '/{suggestions[0]}'?"
    else:
        return f"Unknown command '/{command}'. Type '/help' to see available commands."


def get_sheet_data(sheet_url: str, creds_path: str) -> list[tuple[str, list[list[str]]]]:
    """Fetch all rows from all worksheets of the given Google Sheet."""
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(  # type: ignore
        creds_path, scopes=scopes)  # type: ignore
    gc = gspread.authorize(creds)
    sheet = gc.open_by_url(sheet_url)
    return [(ws.title, ws.get_all_values()) for ws in sheet.worksheets()]


def send_weekly_summary(sheet_url: str, creds_path: str):
    message = format_upcoming_events(sheet_url, creds_path, 3)
    send_message(message)
