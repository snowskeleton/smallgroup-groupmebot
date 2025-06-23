import requests
import time

import commands
import difflib

from bot_secrets import BOT_NAME, BOT_ID


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


def periodic_messages():
    while True:
        time.sleep(3600)  # every hour
        send_message("Just checking in!")


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


