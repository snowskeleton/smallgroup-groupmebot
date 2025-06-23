from flask import Flask, request
import requests
import threading
import time
import difflib

import commands
import storage

from bot_secrets import *

app = Flask(__name__)

def send_message(text: str):
    url = "https://api.groupme.com/v3/bots/post"
    data = {"bot_id": BOT_ID, "text": text}
    requests.post(url, json=data)


@app.route("/healthcheck", methods=["GET"])
def healthcheck():
    return "ok", 200


@app.route("/new_event", methods=["POST"])
def new_event():
    data = request.get_json()
    # print(data)
    sender = data.get("name")
    text = data.get("text")
    message_id = data.get("id")
    created_at = data.get("created_at", 0)
    group_id = data.get("group_id", "")
    sender_id = data.get("sender_id", "")

    if to_or_from_the_bot(sender, text):
        storage.add_message(message_id, created_at, group_id, sender_id)

    # Only process messages from others that are commands
    if sender != BOT_NAME and text:
        response = process_message(sender, text)
        if response:
            send_message(response)

    return "ok", 200


def to_or_from_the_bot(sender: str, text: str):
    if not text:
        return False
    if sender == BOT_NAME:
        return True
    if text.startswith("/"):
        return True
    return False


@app.route("/", methods=["POST", "GET"])
def callback():
    return "ok", 200


@app.route("/oauth/callback", methods=["GET"])
def oauth_callback():
    token = request.args.get("access_token")
    if token:
        storage.save_token(token)
        return "Authentication complete. Token saved."

    # Fallback: standard code exchange
    code = request.args.get("code")
    if not code:
        return "Missing code parameter", 400

    token_url = "https://api.groupme.com/oauth/access_token"

    payload = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code": code,
        "redirect_uri": REDIRECT_URI
    }

    resp = requests.post(token_url, data=payload)

    if resp.ok:
        access_token = resp.json().get("access_token")
        if access_token:
            storage.save_token(access_token)
            return "Authentication complete. Token saved."
        else:
            return "Failed to retrieve access token.", 500
    else:
        return f"Error during token exchange: {resp.text}", 500


# Periodic message thread
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


def check_secrets():
    """Ensure all uppercase variables in bot_secrets are non-empty."""
    import bot_secrets
    for key in dir(bot_secrets):
        if key.isupper():
            value = getattr(bot_secrets, key)
            if not value:
                raise ValueError(f"Missing or empty secret: {key}")


threading.Thread(target=periodic_messages, daemon=True).start()

if __name__ == "__main__":
    check_secrets()
    storage.init_db()
    app.run(host="0.0.0.0", port=5001, debug=True)
