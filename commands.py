from difflib import get_close_matches
from typing import Callable

from requests import delete

from bot_secrets import CLIENT_ID, REDIRECT_URI
from models.Sheet import Sheet, NoSheetLink
from storage import get_all_messages, clear_messages, get_token, save_schedule, save_sheet_link


_command_registry: list[Callable[[str, str], str]] = []

def command(func: Callable[[str, str], str]):
    """Decorator to register bot commands for /help."""
    _command_registry.append(func)
    return func


def process_message(sender: str, text: str) -> str | None:
    """Process incoming message and return a response string if applicable."""
    if not text.startswith("/"):
        return

    parts = text.strip().split(maxsplit=1)
    command_name = parts[0][1:].lower()
    args = parts[1] if len(parts) > 1 else ""

    command_map = {func.__name__: func for func in _command_registry}
    func = command_map.get(command_name)

    if func:
        return func(sender, args)

    suggestions = get_close_matches(
        command_name, command_map.keys(), n=1, cutoff=0.6)
    if suggestions:
        return f"Unknown command '/{command_name}'. Did you mean '/{suggestions[0]}'?"
    return f"Unknown command '/{command_name}'. Type '/help' to see available commands."


@command
def authenticate(sender: str, args: str) -> str:
    """Provides an authentication link for the admin to authorize the bot."""
    auth_url = f"https://oauth.groupme.com/oauth/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}"
    return f"Click here to authenticate: {auth_url}"


@command
def clear(sender: str, args: str) -> str:
    """Deletes recent bot messages from the chat. (Requires admin authentication with the /authenticate command)"""
    messages = get_all_messages()
    token = get_token()
    if not token:
        return "No access token found. Please authenticate with /authenticate."

    success_count = 0
    for msg_id, _, group_id, _ in messages:
        url = f"https://api.groupme.com/v3/conversations/{group_id}/messages/{msg_id}?token={token}"
        resp = delete(url)
        if resp.ok:
            success_count += 1
        else:
            print(f"Failed to delete {msg_id}: {resp.status_code} {resp.text}")

    clear_messages()
    return f"Cleared {success_count} recent bot messages."


@command
def echo(sender: str, args: str) -> str:
    """Repeats whatever text the user provides."""
    return args if args else "(nothing to echo)"


@command
def hello(sender: str, args: str) -> str:
    """Responds with a greeting."""
    return f"Hi, {sender}!"


@command
def help(sender: str, args: str) -> str:
    """Prints this message"""
    response_lines = ["Available commands:"]
    for func in _command_registry:
        doc = func.__doc__ or "(no description)"
        response_lines.append(f"/{func.__name__} - {doc}")
    return "\n".join(response_lines)


@command
def ping(sender: str, args: str) -> str:
    """Responds with 'Pong!'."""
    return "Pong!"


@command
def schedule(sender: str, args: str) -> str:
    """Manage or view the posting schedule. Subcommands: show [count], set <cron>, link <sheet url>."""
    parts = args.strip().split(maxsplit=1)
    subcommand = parts[0].lower() if parts else "show"
    remainder = parts[1] if len(parts) > 1 else ""

    # defaults to 'show 3'
    if subcommand == "show":
        return schedule_show(remainder)

    if subcommand == "set":
        return schedule_set(remainder)

    if subcommand == "link":
        return schedule_link(remainder)

    return "Unknown subcommand.\nUsage:\n\t/schedule show [count]\n\t/schedule set <cron expression>\n\t/schedule link <google sheets link>"


def schedule_show(count: str) -> str:
    working_count = 3
    if count.isdigit():
        working_count = int(count)
    try:
        return Sheet().formatted_upcoming_events(working_count)
    except NoSheetLink as e:
        return repr(e)


def schedule_set(schedule: str) -> str:
    if not schedule:
        return "Please provide a cron expression (e.g., '* * * * *')."
    stripped_schedule = schedule.strip()
    save_schedule(stripped_schedule)
    return f"Updated posting schedule to: {stripped_schedule}"


def schedule_link(link: str) -> str:
    if not link:
        return "Please provide the Google Sheet URL."
    stripped_link = link.strip()
    save_sheet_link(stripped_link)
    return f"Updated sheet link to: {stripped_link}"
