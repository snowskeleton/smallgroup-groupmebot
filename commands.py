import sys
# import requests
import storage

from bot_secrets import CLIENT_ID, REDIRECT_URI
def echo(sender: str, args: str) -> str:
    """Repeats whatever text the user provides."""
    return args if args else "(nothing to echo)"

def hello(sender: str, args: str) -> str:
    """Responds with a greeting."""
    return f"Hi, {sender}!"

def help(sender: str, args: str) -> str:
    """Prints this message"""
    response_lines = ["Available commands:"]
    current_module = sys.modules[__name__]
    for name in dir(current_module):
        func = getattr(current_module, name)
        if callable(func) and not name.startswith("__"):
            doc = func.__doc__ or "(no description)"
            response_lines.append(f"/{name} - {doc}")
    return "\n".join(response_lines)

def ping(sender: str, args: str) -> str:
    """Responds with 'Pong!'."""
    return "Pong!"


def clear(sender: str, args: str) -> str:
    """Deletes recent bot messages from the chat."""
    message_ids = storage.get_all_messages()
    success_count = 0

    for msg_id in message_ids:
        url = f"https://api.groupme.com/v3/bots/post"
        # GroupMe doesn't provide a message deletion API for bots; adjust if full API access exists
        # Assuming privileged token use:
        # url = f"https://api.groupme.com/v3/groups/{GROUP_ID}/messages/{msg_id}"
        # requests.delete(url, headers={"X-Access-Token": USER_ACCESS_TOKEN})

        # For placeholder logic:
        print(f"Pretend deleting message: {msg_id}")
        success_count += 1

    storage.clear_messages()
    return f"Cleared {success_count} recent bot messages."


def authenticate(sender: str, args: str) -> str:
    """Provides an authentication link for the admin to authorize the bot."""
    auth_url = f"https://oauth.groupme.com/oauth/authorize?client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}"
    return f"Click here to authenticate: {auth_url}"
