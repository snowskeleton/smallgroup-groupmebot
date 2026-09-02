from croniter import croniter
from datetime import datetime, timedelta
from pytz import timezone
from typing import Dict

from requests import post
from time import sleep

from commands import schedule_generate, schedule_show
from config import BOT_ID, BOT_NAME, TIMEZONE
from exceptions import NoAuthenticationToken
from log import log
from models.Event import Event
from models.Sheet import Sheet
from storage import get_schedule, get_token, get_group_id


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
    local_tz = timezone(TIMEZONE)
    cron_schedule = get_schedule()
    if cron_schedule:
        now = datetime.now(local_tz)

        # Truncate seconds for a clean comparison
        base = now.replace(second=0, microsecond=0)

        if croniter.match(cron_schedule, base):
            # Top the sheet up first, so the post reflects any rows we just
            # added. Generation only appends, so running it repeatedly is safe.
            try:
                log("INFO", "utils", schedule_generate())
            except Exception as e:
                log("ERROR", "utils", f"Failed to generate schedule: {e}")
            send_message(schedule_show("3", email=True))


def send_next_calendar_event(count: int = 1):
    sheet = Sheet.get_instance()
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

    eastern = timezone(TIMEZONE)
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
        "timezone": TIMEZONE,
        "description": event.notes,
        "is_all_day": False,
        "location": {"name": event.location_display}
    }

    resp = post(url, headers=headers, json=payload)
    if resp.ok:
        log("INFO", "utils", f"Event '{payload['name']}' created successfully.")
    else:
        log("ERROR", "utils", f"Failed to create event: {resp.status_code} {resp.text}")
