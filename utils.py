from croniter import croniter
from datetime import datetime, timedelta
from difflib import get_close_matches
from pytz import timezone
from typing import Dict

from requests import post
from time import sleep

import commands

from commands import schedule_show
from bot_secrets import BOT_NAME, BOT_ID
from storage import get_schedule, get_token, get_group_id

from models.Sheet import Sheet


def check_secrets():
    """Ensure all uppercase variables in bot_secrets are non-empty."""
    import bot_secrets
    for key in dir(bot_secrets):
        if key.isupper():
            value = getattr(bot_secrets, key)
            if not value:
                raise ValueError(f"Missing or empty secret: {key}")


def to_or_from_the_bot(sender: str, text: str) -> bool:
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
    post(url, json=data)


def periodic_messages():
    local_tz = timezone("America/New_York")

    while True:
        cron_schedule = get_schedule()
        if cron_schedule:
            now = datetime.now(local_tz)

            # Truncate seconds for a clean comparison
            base = now.replace(second=0, microsecond=0)

            if croniter.match(cron_schedule, base):
                send_message(schedule_show("3"))

        # --- Check for events to create for tomorrow ---
        sheet = Sheet()
        tomorrow = datetime.now().date() + timedelta(days=1)

        for event in sheet.events:
            if event.date().date() == tomorrow:
                group_id = get_group_id()
                if not group_id:
                    return
                create_groupme_event(
                    group_id,
                    f"{event.date_str} - {event.leader}'s Event",
                    event.date(),
                    event.date() + timedelta(hours=1),
                    str(event),
                    event.location_display
                )
        # ------------------------------------------------
        sleep(60)


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
    suggestions = get_close_matches(command, available, n=1, cutoff=0.6)

    if suggestions:
        return f"Unknown command '/{command}'. Did you mean '/{suggestions[0]}'?"
    else:
        return f"Unknown command '/{command}'. Type '/help' to see available commands."


# --- GroupMe Event Creation ---
def create_groupme_event(group_id: str, name: str, start_at: datetime, end_at: datetime, description: str, location_name: str, location_address: str = ""):
    token = get_token()
    if not token:
        print("Admin token not set. Please authenticate.")
        return

    url = f"https://api.groupme.com/v3/conversations/{group_id}/events/create"
    headers = {"X-Access-Token": token}

    payload: Dict[str, str | int | bool | Dict[str, str]] = {
        "name": name,
        "start_at": start_at.isoformat(),
        "end_at": end_at.isoformat(),
        "timezone": "America/New_York",
        "description": description,
        "is_all_day": True,
        "location": {"name": location_name}
    }

    if location_address:
        payload["location"]["address"] = location_address

    resp = post(url, headers=headers, json=payload)
    if resp.ok:
        print(f"Event '{name}' created successfully.")
    else:
        print(f"Failed to create event: {resp.status_code} {resp.text}")
