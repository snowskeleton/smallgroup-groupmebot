from flask import Flask, request
import requests
import threading
import time
import difflib

import commands

app = Flask(__name__)
BOT_ID = "80e62ea5791dc1f37728b7ff2d"
BOT_NAME = "Test Bot"

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
    print(data)
    sender = data.get("name")
    text = data.get("text")

    if sender != BOT_NAME and text:
        response = process_message(sender, text)
        if response:
            send_message(response)

    return "ok", 200

@app.route("/", methods=["POST", "GET"])
def callback():
    return "ok", 200

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

threading.Thread(target=periodic_messages, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
