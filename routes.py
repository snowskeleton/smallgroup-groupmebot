from flask import Flask, request
from requests import post

from commands import process_message
from storage import save_group_id, save_message, save_token
try:
    from bot_secrets import *
except ImportError:
    print("\n\t[ERROR] Missing 'bot_secrets.py'.\n")
    import sys
    sys.exit(1)
from utils import to_or_from_the_bot, send_message

app = Flask(__name__)

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

    save_group_id(group_id)
    if to_or_from_the_bot(sender, text):
        save_message(message_id, created_at, group_id, sender_id)

    # Only process messages from others that are commands
    if sender != BOT_NAME and text:
        response = process_message(sender, text)
        if response:
            send_message(response)

    return "ok", 200


@app.route("/", methods=["POST", "GET"])
def callback():
    return "ok", 200


@app.route("/oauth/callback", methods=["GET"])
def oauth_callback():
    token = request.args.get("access_token")
    if token:
        save_token(token)
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

    resp = post(token_url, data=payload)

    if resp.ok:
        access_token = resp.json().get("access_token")
        if access_token:
            save_token(access_token)
            return "Authentication complete. Token saved."
        else:
            return "Failed to retrieve access token.", 500
    else:
        return f"Error during token exchange: {resp.text}", 500


