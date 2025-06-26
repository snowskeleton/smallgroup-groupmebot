from croniter import croniter
from datetime import datetime, timedelta
from pytz import timezone
from typing import Dict

from requests import post
from time import sleep

from commands import schedule_show
from bot_secrets import BOT_NAME, BOT_ID
from exceptions import NoAuthenticationToken
from models.Event import Event
from models.Sheet import Sheet
from storage import get_schedule, get_token, get_group_id


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
    while True:
        send_scheduled_schedule()
        # this needs logic to only create it a day ahead of time and not create duplicate events
        # send_next_calendar_event()
        sleep(60)


def send_scheduled_schedule():
    local_tz = timezone("America/New_York")
    cron_schedule = get_schedule()
    if cron_schedule:
        now = datetime.now(local_tz)

        # Truncate seconds for a clean comparison
        base = now.replace(second=0, microsecond=0)

        if croniter.match(cron_schedule, base):
            send_message(schedule_show("3"))


def send_next_calendar_event(count: int = 1):
    sheet = Sheet()
    for event in sheet.upcoming_events(count):
        create_groupme_event(event)


def create_groupme_event(event: Event):
    token = ""
    try:
        token = get_token()
    except NoAuthenticationToken as e:
        send_message(repr(e))

    group_id = get_group_id()

    url = f"https://api.groupme.com/v3/conversations/{group_id}/events/create"
    headers = {"X-Access-Token": token}

    eastern = timezone("America/New_York")
    # Combine date and time
    start_at = event.date()
    if event.event_time:
        time_obj = datetime.strptime(event.event_time, "%I:%M %p").time()
        start_at = start_at.replace(hour=time_obj.hour, minute=time_obj.minute)

    start_at = start_at.astimezone(eastern)
    end_at = (start_at + timedelta(hours=2))

    payload: Dict[str, str | int | bool | Dict[str, str]] = {
        "name": f"{event.date_str} – Small Group ft. {event.leader}",
        "start_at": start_at.isoformat(),
        "end_at": end_at.isoformat(),
        "timezone": "America/New_York",
        "description": event.notes,
        "is_all_day": False,
        "location": {"name": event.location_display}
    }

    resp = post(url, headers=headers, json=payload)
    if resp.ok:
        print(f"Event '{payload['name']}' created successfully.")
    else:
        print(f"Failed to create event: {resp.status_code} {resp.text}")
