import requests

from typing import Callable

from storage import get_all_messages, clear_messages, get_token, save_schedule

from bot_secrets import CLIENT_ID, REDIRECT_URI


_command_registry: list[Callable[[str, str], str]] = []


def command(func: Callable[[str, str], str]):
    """Decorator to register bot commands for /help."""
    _command_registry.append(func)
    return func


@command
def echo(sender: str, args: str) -> str:
    """Repeats whatever text the user provides."""
    return args if args else "(nothing to echo)"


@command
def hello(sender: str, args: str) -> str:
    """Responds with a greeting."""
    return f"Hi, {sender}!"


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
def clear(sender: str, args: str) -> str:
    """Deletes recent bot messages from the chat. (Requires admin authentication with the /authenticate command)"""
    messages = get_all_messages()
    token = get_token()
    if not token:
        return "No access token found. Please authenticate with /authenticate."

    success_count = 0
    for msg_id, _, group_id, _ in messages:
        url = f"https://api.groupme.com/v3/conversations/{group_id}/messages/{msg_id}?token={token}"
        resp = requests.delete(url)
        if resp.ok:
            success_count += 1
        else:
            print(f"Failed to delete {msg_id}: {resp.status_code} {resp.text}")

    clear_messages()
    return f"Cleared {success_count} recent bot messages."


@command
def authenticate(sender: str, args: str) -> str:
    """Provides an authentication link for the admin to authorize the bot."""
    auth_url = f"https://oauth.groupme.com/oauth/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}"
    return f"Click here to authenticate: {auth_url}"


@command
def schedule(sender: str, args: str) -> str:
    """Updates the posting schedule. Format should be cron-like (e.g., '* * * * *')."""
    if not args:
        return "Please provide a cron-style schedule (e.g., '* * * * *')."
    save_schedule(args.strip())
    return f"Updated posting schedule to: {args.strip()}"
